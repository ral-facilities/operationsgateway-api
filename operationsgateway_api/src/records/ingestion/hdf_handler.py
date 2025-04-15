from datetime import datetime
import logging
from tempfile import SpooledTemporaryFile
from typing import Any, Literal

import h5py
from pydantic import ValidationError

from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.constants import DATA_DATETIME_FORMAT, ID_DATETIME_FORMAT
from operationsgateway_api.src.exceptions import HDFDataExtractionError, ModelError
from operationsgateway_api.src.models import (
    ChannelManifestModel,
    FloatImageChannelMetadataModel,
    FloatImageChannelModel,
    FloatImageModel,
    ImageChannelMetadataModel,
    ImageChannelModel,
    ImageModel,
    RecordMetadataModel,
    RecordModel,
    ScalarChannelMetadataModel,
    ScalarChannelModel,
    VectorChannelMetadataModel,
    VectorChannelModel,
    VectorModel,
    WaveformChannelMetadataModel,
    WaveformChannelModel,
    WaveformModel,
)
from operationsgateway_api.src.records.float_image import FloatImage
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.ingestion.channel_checks import ChannelChecks
from operationsgateway_api.src.records.vector import Vector
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()


class HDFDataHandler:
    acceptable_datasets = {
        "scalar": ["data"],
        "image": ["data"],
        "float_image": ["data"],
        "waveform": ["x", "y"],
        "vector": ["data"],
    }

    def __init__(self, hdf_temp_file: SpooledTemporaryFile) -> None:
        """
        Convert a HDF file that comes attached in a HTTP request (not in HDF format)
        into a HDF file via h5py
        """
        self.hdf_file = h5py.File(hdf_temp_file, "r")
        self.channels = {}
        self.waveforms = []
        self.images = []
        self.float_images = []
        self.vectors = []

    async def extract_data(
        self,
    ) -> tuple[
        RecordModel,
        list[WaveformModel],
        list[ImageModel],
        list[FloatImageModel],
        list[VectorModel],
        list[dict[str, str]],
    ]:
        """
        Extract data from a HDF file that is formatted in the OperationsGateway data
        structure format. Metadata of the shot, channel data and its metadata is
        extracted
        """
        log.debug("Extracting data from HDF files")

        metadata_hdf = dict(self.hdf_file.attrs)
        try:
            metadata_hdf["timestamp"] = datetime.strptime(
                metadata_hdf["timestamp"],
                DATA_DATETIME_FORMAT,
            )
        except (KeyError, ValueError) as exc:
            raise HDFDataExtractionError(
                f"Invalid timestamp metadata. Expected key 'timestamp' with value formatted as '{DATA_DATETIME_FORMAT}'."
            ) from exc

        self.record_id = metadata_hdf["timestamp"].strftime(ID_DATETIME_FORMAT)
        await self.extract_channels()

        try:
            record = RecordModel(
                _id=self.record_id,
                metadata=RecordMetadataModel(**metadata_hdf),
                channels=self.channels,
            )
        except ValidationError as exc:
            raise ModelError(str(exc)) from exc

        return (
            record,
            self.waveforms,
            self.images,
            self.float_images,
            self.vectors,
            self.internal_failed_channel,
        )

    def _unexpected_attribute(self, channel_type, value):
        """
        tells the location it is called whether to stop. Stops if the value for data
        is not the same what it is meant to be for the channel type
        using the self.acceptable_datasets dictionary
        """
        return any(val != self.acceptable_datasets[channel_type][0] for val in value)

    def _extract_image(
        self,
        internal_failed_channel,
        channel_name,
        channel_metadata,
        value,
    ):
        """
        Extract data for images in the HDF file and place the data into
        relevant Pydantic models as well as performing on image specific checks
        """
        image_path = Image.get_relative_path(self.record_id, channel_name)

        if self._unexpected_attribute("image", value):
            internal_failed_channel.append(
                {channel_name: "unexpected group or dataset in channel group"},
            )
            return None, internal_failed_channel

        try:
            metadata = ImageChannelMetadataModel(**channel_metadata)
            channel = ImageChannelModel(metadata=metadata, image_path=image_path)
            image_model = ImageModel(
                path=image_path,
                data=value["data"][()],
                bit_depth=metadata.bit_depth,
            )
            self.images.append(image_model)

            return channel, False
        except KeyError:
            internal_failed_channel.append(
                {channel_name: "data attribute is missing"},
            )
            return None, internal_failed_channel
        except ValidationError as exc:
            raise ModelError(str(exc)) from exc

    def _extract_float_image(
        self,
        internal_failed_channel: list[dict[str, str]],
        channel_name: str,
        channel_metadata: dict,
        value: Any,
    ) -> (
        tuple[FloatImageChannelModel, Literal[False]]
        | tuple[None, list[dict[str, str]]]
    ):
        """
        Extract data for float images in the HDF file and place the data into
        relevant Pydantic models as well as performing float image specific checks.
        """
        image_path = FloatImage.get_relative_path(self.record_id, channel_name)

        if self._unexpected_attribute("float_image", value):
            internal_failed_channel.append(
                {channel_name: "unexpected group or dataset in channel group"},
            )
            return None, internal_failed_channel

        try:
            metadata = FloatImageChannelMetadataModel(**channel_metadata)
            channel = FloatImageChannelModel(
                metadata=metadata,
                image_path=image_path,
            )
            image_model = FloatImageModel(
                path=image_path,
                data=value["data"][()],
            )
            self.float_images.append(image_model)

            return channel, False
        except KeyError:
            internal_failed_channel.append(
                {channel_name: "data attribute is missing"},
            )
            return None, internal_failed_channel
        except ValidationError as exc:
            raise ModelError(str(exc)) from exc

    def _extract_scalar(
        self,
        internal_failed_channel,
        channel_name,
        channel_metadata,
        value,
    ):
        """
        Extract data for scalars in the HDF file and place the data into
        relevant Pydantic models as well as performing on scalar specific checks
        """
        if self._unexpected_attribute("scalar", value):
            internal_failed_channel.append(
                {channel_name: "unexpected group or dataset in channel group"},
            )
            return None, internal_failed_channel

        try:
            channel = ScalarChannelModel(
                metadata=ScalarChannelMetadataModel(**channel_metadata),
                data=value["data"][()],
            )
            return channel, False
        except KeyError:
            internal_failed_channel.append(
                {channel_name: "data attribute is missing"},
            )
            return None, internal_failed_channel
        except ValidationError as exc:
            for error in exc.errors():
                if (
                    error["type"] == "int_type"
                    or error["type"] == "float_type"
                    or error["type"] == "string_type"
                ):
                    internal_failed_channel.append(
                        {channel_name: "data has wrong datatype"},
                    )
                    break
                else:
                    raise ModelError(str(exc)) from exc
            return None, internal_failed_channel

    def _extract_waveform(
        self,
        internal_failed_channel,
        channel_name,
        channel_metadata,
        value,
    ):
        """
        Extract data for waveforms in the HDF file and place the data into
        relevant Pydantic models as well as performing on waveform specific checks
        """
        waveform_path = Waveform.get_relative_path(self.record_id, channel_name)
        log.debug("Waveform Path: %s", waveform_path)

        value_list = []
        for val in value:
            value_list.append(val)
        if (list(set(value_list) - set(self.acceptable_datasets["waveform"]))) != []:
            internal_failed_channel.append(
                {channel_name: "unexpected group or dataset in channel group"},
            )
            return None, internal_failed_channel

        try:
            channel = WaveformChannelModel(
                metadata=WaveformChannelMetadataModel(**channel_metadata),
                waveform_path=waveform_path,
            )

            self.waveforms.append(
                WaveformModel(
                    path=waveform_path,
                    x=value["x"][()],
                    y=value["y"][()],
                ),
            )

            return channel, False
        except KeyError:
            for key in ["x", "y"]:
                try:
                    value[key]
                except KeyError:
                    internal_failed_channel.append(
                        {channel_name: f"{key} attribute is missing"},
                    )
            return None, internal_failed_channel
        except ValidationError as exc:
            raise ModelError(str(exc)) from exc

    def _extract_vector(
        self,
        internal_failed_channel: list[dict[str, str]],
        channel_name: str,
        channel_metadata: dict,
        value: Any,
    ) -> tuple[VectorChannelModel, Literal[False]] | tuple[None, list[dict[str, str]]]:
        """
        Extract data for a vector in the HDF file and place the data into
        relevant Pydantic models.
        """
        relative_path = Vector.get_relative_path(self.record_id, channel_name)

        if self._unexpected_attribute("vector", value):
            internal_failed_channel.append(
                {channel_name: "unexpected group or dataset in channel group"},
            )
            return None, internal_failed_channel

        try:
            metadata = VectorChannelMetadataModel(**channel_metadata)
            channel = VectorChannelModel(
                metadata=metadata,
                vector_path=relative_path,
            )
            model = VectorModel(
                path=relative_path,
                data=value["data"][()],
            )
            self.vectors.append(model)

            return channel, False
        except KeyError:
            internal_failed_channel.append(
                {channel_name: "data attribute is missing"},
            )
            return None, internal_failed_channel
        except ValidationError as exc:
            raise ModelError(str(exc)) from exc

    async def _extract_channel(
        self,
        channel_name: str,
        value: Any,
        manifest: ChannelManifestModel,
        internal_failed_channel: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        channel_metadata = dict(value.attrs)
        channel_checks = ChannelChecks(
            ingested_record={channel_name: channel_metadata},
        )
        channel_checks.set_channels(manifest)
        response = await channel_checks.channel_dtype_checks()
        if response != []:
            internal_failed_channel.extend(response)
            return internal_failed_channel
        elif value.attrs["channel_dtype"] == "image":
            channel, fail = self._extract_image(
                internal_failed_channel,
                channel_name,
                channel_metadata,
                value,
            )
        elif value.attrs["channel_dtype"] == "float_image":
            channel, fail = self._extract_float_image(
                internal_failed_channel,
                channel_name,
                channel_metadata,
                value,
            )
        elif value.attrs["channel_dtype"] == "rgb-image":
            # TODO - implement colour image ingestion. Currently waiting on the
            # OG-HDF5 converter to support conversion of colour images.
            # Implementation will be as per greyscale image (`get_relative_path()`
            # then append to `self.images`) but might require extracting a different
            # part of the value
            raise HDFDataExtractionError("Colour images cannot be ingested")
        elif value.attrs["channel_dtype"] == "scalar":
            channel, fail = self._extract_scalar(
                internal_failed_channel,
                channel_name,
                channel_metadata,
                value,
            )
        elif value.attrs["channel_dtype"] == "waveform":
            channel, fail = self._extract_waveform(
                internal_failed_channel,
                channel_name,
                channel_metadata,
                value,
            )
        elif value.attrs["channel_dtype"] == "vector":
            channel, fail = self._extract_vector(
                internal_failed_channel,
                channel_name,
                channel_metadata,
                value,
            )

        if fail:
            internal_failed_channel = fail
        else:
            # Put channels into a dictionary to give a good structure to query them in
            # the database
            self.channels[channel_name] = channel

        return internal_failed_channel

    async def extract_channels(self) -> None:
        """
        Extract data from each data channel in the HDF file and place the data into
        relevant Pydantic models
        """
        internal_failed_channel = []
        manifest = await ChannelManifest.get_most_recent_manifest()
        for channel_name, value in self.hdf_file.items():
            internal_failed_channel = await self._extract_channel(
                channel_name=channel_name,
                value=value,
                manifest=manifest,
                internal_failed_channel=internal_failed_channel,
            )
        self.internal_failed_channel = internal_failed_channel

    @staticmethod
    def _update_data(
        checker_response: dict[str, Any],
        record_data: RecordModel,
        images: list[ImageModel],
        float_images: list[FloatImageModel],
        waveforms: list[WaveformModel],
        vectors: list[VectorModel],
    ) -> tuple[
        RecordModel,
        list[ImageModel],
        list[FloatImageModel],
        list[WaveformModel],
        list[VectorModel],
    ]:
        for key in checker_response["rejected_channels"].keys():
            try:
                channel = record_data.channels[key]
            except KeyError:
                continue

            if channel.metadata.channel_dtype == "image":
                HDFDataHandler.remove_channel(images, channel.image_path)
            elif channel.metadata.channel_dtype == "float_image":
                HDFDataHandler.remove_channel(float_images, channel.image_path)
            elif channel.metadata.channel_dtype == "waveform":
                HDFDataHandler.remove_channel(waveforms, channel.waveform_path)
            elif channel.metadata.channel_dtype == "vector":
                HDFDataHandler.remove_channel(vectors, channel.vector_path)

            del record_data.channels[key]

        return record_data, images, float_images, waveforms, vectors

    @staticmethod
    def remove_channel(
        models: (
            list[ImageModel]
            | list[FloatImageModel]
            | list[WaveformModel]
            | list[VectorModel]
        ),
        path: str,
    ) -> None:
        """Removes the model from models with the specified path, if found."""
        for model in models:
            if model.path == path:
                return models.remove(model)

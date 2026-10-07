from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image as PILImage

from operationsgateway_api.src.exceptions import (
    EchoS3Error,
    MissingAttributeError,
    QueryParameterError,
    RecordError,
)
from operationsgateway_api.src.models import (
    ChannelDtype,
    ImageModel,
    PartialImageSeriesChannelModel,
)
from operationsgateway_api.src.records.echo_interface import get_echo_interface
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.image_abc import ImageABC
from operationsgateway_api.src.records.record import Record


# pretty much a copy paste from the image class
class ImageSeries(ImageABC):
    echo_prefix = "image_series"
    echo_extension = "npy"
    storage_dtype = np.dtype("<u2")

    def __init__(self, image: ImageModel) -> None:
        super().__init__(image)

    def write_npy_header(self, file_object: BytesIO, shape: tuple[int, ...]) -> None:
        # before the numpy data (of images) we write a header so we
        # know what the data contains
        np.lib.format.write_array_header_1_0(
            file_object,
            {
                "descr": np.lib.format.dtype_to_descr(self.storage_dtype),
                "fortran_order": False,  # makes sure the data is stored in series order
                "shape": shape,  # [number of images, height, width]
            },
        )

    def get_header_offset_bytes(self, data: np.ndarray) -> int:
        header = BytesIO()
        self.write_npy_header(header, data.shape)
        return header.tell()

    def create_thumbnail(self) -> None:
        # Use a separate copy of frame zero for PNG processing.
        preview = Image(
            ImageModel(
                path=self.image.path,
                data=self.image.data[0].copy(),
                bit_depth=self.image.bit_depth,
            ),
        )
        preview.create_thumbnail()
        self.thumbnail = preview.thumbnail

    @staticmethod
    async def upload_image(input_image: ImageSeries) -> str | None:
        # Convert for storage without rescaling pixel values.
        data = np.ascontiguousarray(
            input_image.image.data,
            dtype=input_image.storage_dtype,
        )

        image_bytes = BytesIO()
        input_image.write_npy_header(image_bytes, data.shape)

        # Append the contiguous pixel bytes after the header.
        image_bytes.write(data.data.cast("B"))

        storage_path = input_image.get_full_path(input_image.image.path)

        try:
            await get_echo_interface().upload_file_object(image_bytes, storage_path)
            return None
        except EchoS3Error:
            return input_image.get_channel_name_from_path()

    @staticmethod
    async def get_frame(
        record_id: str,
        channel_name: str,
        frame_index: int,
    ) -> bytes:
        """
        This doesn't just get any old frame! but it works out where each frame
        is by calculate the requested frame's byte range. It uses the header offset,
        frame index, dimensions, and bytes per pixel, then retrieve it as a
        greyscale PNG.
        """

        record = await Record.find_record_by_id(record_id, {})
        channel = (record.channels or {}).get(channel_name)

        if channel is None:
            raise MissingAttributeError(
                f"Channel '{channel_name}' not found in record '{record_id}'",
            )

        if not isinstance(channel, PartialImageSeriesChannelModel):
            raise QueryParameterError("Channel is not an image series")

        metadata = channel.metadata
        if metadata is None or metadata.channel_dtype != ChannelDtype.IMAGE_SERIES:
            raise RecordError("Image series metadata is missing or invalid")

        shape = channel.shape
        header_offset = channel.header_offset_bytes
        image_path = channel.image_path

        if (
            shape is None
            or any(dimension <= 0 for dimension in shape)
            or header_offset is None
            or header_offset <= 0
            or not image_path
        ):
            raise RecordError("Image series storage metadata is missing or invalid")

        frame_count, height, width = shape

        if not 0 <= frame_index < frame_count:
            raise QueryParameterError(
                f"Frame index must be between 0 and {frame_count - 1}",
            )

        # Each frame occupies consecutive bytes after the NPY header.
        frame_size = height * width * ImageSeries.storage_dtype.itemsize
        start_byte = header_offset + frame_index * frame_size
        end_byte = start_byte + frame_size - 1

        pixel_bytes = await get_echo_interface().download_file_range(
            object_path=ImageSeries.get_full_path(image_path),
            start_byte=start_byte,
            end_byte=end_byte,
        )

        frame = np.frombuffer(
            pixel_bytes,
            dtype=ImageSeries.storage_dtype,
        ).reshape(height, width)

        output = BytesIO()
        with PILImage.fromarray(frame) as image:
            image.save(output, format="PNG")

        return output.getvalue()

    @staticmethod
    async def get_image(
        record_id: str,
        channel_name: str,
        colourmap_name: str,
    ) -> BytesIO:
        # needed because we're an abstract class
        raise NotImplementedError(
            "TDDO: Frame retrieval will be implemented later",
        )

    @staticmethod
    async def get_preferred_colourmap(access_token: str) -> str:
        return await Image.get_preferred_colourmap(access_token)

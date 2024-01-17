import base64
from io import BytesIO
import json
import logging

from botocore.exceptions import ClientError
import matplotlib.pyplot as plt

from operationsgateway_api.src.exceptions import EchoS3Error, WaveformError
from operationsgateway_api.src.models import WaveformModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.echo_interface import EchoInterface


log = logging.getLogger()


class Waveform:
    def __init__(self, waveform: WaveformModel) -> None:
        self.waveform = waveform
        self.thumbnail = None
        self.is_stored = False

    def to_json(self):
        """
        Use `self.waveform` and return a JSON file stored in a BytesIO object
        """
        b = BytesIO()
        b.write(self.waveform.model_dump_json(by_alias=True, indent=2).encode())
        b.seek(0)
        return b

    async def insert_waveform(self) -> None:
        """
        If the waveform stored in this object isn't already stored in the database,
        insert it in the waveforms collection
        """
        echo = EchoInterface()
        await self._is_waveform_stored(echo)
        if not self.is_stored:
            bytes_json = self.to_json()
            echo.upload_file_object(
                bytes_json,
                f"waveforms/{Waveform.convert_id_to_path(self.waveform.id_)}",
            )

    def create_thumbnail(self) -> None:
        """
        Create a thumbnail of the waveform data and store it in this object
        """
        with BytesIO() as waveform_image_buffer:
            self._create_plot(waveform_image_buffer)
            self.thumbnail = base64.b64encode(waveform_image_buffer.getvalue())

    def get_channel_name_from_id(self) -> str:
        """
        From a waveform ID, extract and return the channel name associated with the
        waveform. For example, 20220408140310_N_COMP_SPEC_TRACE -> N_COMP_SPEC_TRACE
        """
        return "_".join(self.waveform.id_.split("_")[1:])
    
    @staticmethod
    def convert_id_to_path(waveform_id: str) -> str:
        """
        TODO
        """
        id_ = waveform_id.split("_")[0]
        channel_name = waveform_id.split("_")[1:]

        # Covers a situation where the channel name contains underscores
        channel_name = "_".join(channel_name) if len(channel_name) > 1 else channel_name[0]
        return f'{"/".join([id_, channel_name])}.json'

    async def _is_waveform_stored(self, echo: EchoInterface) -> bool:
        """
        Use the object's waveform ID to detect whether it is stored in MongoDB and
        return the appropriate boolean depending on the result of the MongoDB query
        """
        waveform_exist = await MongoDBInterface.find_one(
            "waveforms",
            filter_={"_id": self.waveform.id_},
        )
        self.is_stored = True if waveform_exist else False

    def _create_plot(self, buffer) -> None:
        """
        Using Matplotlib, create a plot of the waveform data and save it to a bytes IO
        object provided as a parameter to this function
        """
        # Making changes to plot so figure size and line width is correct and axes are
        # disabled
        plt.rcParams["figure.figsize"] = [1, 0.75]
        plt.xticks([])
        plt.yticks([])
        plt.plot(
            self.waveform.x,
            self.waveform.y,
            linewidth=0.5,
        )
        plt.axis("off")
        plt.box(False)

        plt.savefig(buffer, format="PNG", bbox_inches="tight", pad_inches=0, dpi=130)
        # Flushes the plot to remove data from previously ingested waveforms
        plt.clf()

    @staticmethod
    async def get_waveform(waveform_id: str) -> WaveformModel:
        """
        Given a waveform ID, find the waveform that's stored in MongoDB. This function
        assumes that the waveform should exist; if no waveform can be found, a
        `MissingDocumentError` will be raised
        """
        echo = EchoInterface()
    
        try:
            waveform_path = Waveform.convert_id_to_path(waveform_id)
            waveform_file = echo.download_file_object(f"waveforms/{waveform_path}")
            waveform_data = json.loads(waveform_file.getvalue().decode())
            return WaveformModel(**waveform_data)
        except (ClientError, EchoS3Error) as exc:
            log.error("Waveform could not be found: %s", waveform_path)
            raise WaveformError(
                f"Waveform could not be found on object storage: {waveform_path}",
            )

import base64
from io import BytesIO
import json
import logging

from botocore.exceptions import ClientError
import matplotlib.pyplot as plt

from operationsgateway_api.src.exceptions import EchoS3Error, WaveformError
from operationsgateway_api.src.models import WaveformModel
from operationsgateway_api.src.records.echo_interface import EchoInterface


log = logging.getLogger()


class Waveform:
    echo_prefix = "waveforms"

    def __init__(self, waveform: WaveformModel) -> None:
        self.waveform = waveform
        self.thumbnail = None
        self.is_stored = False

    def to_json(self):
        """
        Use `self.waveform` and return a JSON file stored in a BytesIO object
        """
        b = BytesIO()
        b.write(self.waveform.model_dump_json(indent=2).encode())
        b.seek(0)
        return b

    async def insert_waveform(self) -> None:
        """
        If the waveform stored in this object isn't already stored in the database,
        insert it in the waveforms collection
        """
        bytes_json = self.to_json()
        echo = EchoInterface()
        echo.upload_file_object(
            bytes_json,
            Waveform.get_full_path(self.waveform.path),
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
        From a waveform path, extract and return the channel name associated with the
        waveform. For example, 20220408140310/N_COMP_SPEC_TRACE.json -> N_COMP_SPEC_TRACE

        20220408140310/N_COMP_SPEC_TRACE.json
        """
        filename = self.waveform.path.split("/")[1:][0]
        channel_name = filename.split(".json")[0]
        return channel_name

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
    def get_relative_path(record_id: str, channel_name: str) -> str:
        """
        TODO, base it off get_image_path()
        """
        return f"{record_id}/{channel_name}.json"

    @staticmethod
    def get_full_path(relative_path: str) -> str:
        return f"{Waveform.echo_prefix}/{relative_path}"

    @staticmethod
    async def get_waveform(waveform_path: str) -> WaveformModel:
        """
        Given a waveform path, find the waveform that's stored in MongoDB. This function
        assumes that the waveform should exist; if no waveform can be found, a
        `MissingDocumentError` will be raised
        """
        echo = EchoInterface()
    
        try:
            waveform_file = echo.download_file_object(
                Waveform.get_full_path(waveform_path),
            )
            waveform_data = json.loads(waveform_file.getvalue().decode())
            return WaveformModel(**waveform_data)
        except (ClientError, EchoS3Error) as exc:
            log.error("Waveform could not be found: %s", waveform_path)
            raise WaveformError(
                f"Waveform could not be found on object storage: {waveform_path}",
            ) from exc

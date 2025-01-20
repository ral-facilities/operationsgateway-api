import base64
from io import BytesIO
import json
import logging
from typing import Optional

from botocore.exceptions import ClientError
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: I202

from operationsgateway_api.src.config import Config
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

    def insert_waveform(self)  -> Optional[str]:
        """
        Store the waveform from this object in Echo
        """
        log.info("Storing waveform: %s", self.waveform.path)
        bytes_json = self.to_json()
        echo = EchoInterface()
        try:
            echo.upload_file_object(
                bytes_json,
                Waveform.get_full_path(self.waveform.path),
            )
            return None  # Successful upload
        except EchoS3Error as e:
            # Extract the channel name and propagate it
            channel_name = self.get_channel_name_from_id()
            log.error("Failed to upload waveform for channel '%s': %s", channel_name, str(e))
            return channel_name

    def create_thumbnail(self) -> None:
        """
        Create a thumbnail of the waveform data and store it in this object
        """
        with BytesIO() as waveform_image_buffer:
            self._create_thumbnail_plot(waveform_image_buffer)
            self.thumbnail = base64.b64encode(waveform_image_buffer.getvalue())

    def get_fullsize_png(self, x_label, y_label) -> bytes:
        """
        Create a full size of the waveform data and return it
        """
        with BytesIO() as waveform_image_buffer:
            self._create_fullsize_plot(waveform_image_buffer, x_label, y_label)
            return waveform_image_buffer.getvalue()

    def get_channel_name_from_id(self) -> str:
        """
        From a waveform path, extract and return the channel name associated with the
        waveform.
        For example, 20220408140310/N_COMP_SPEC_TRACE.json -> N_COMP_SPEC_TRACE
        """
        filename = self.waveform.path.split("/")[1:][0]
        channel_name = filename.split(".json")[0]
        return channel_name

    def _create_thumbnail_plot(self, buffer) -> None:
        """
        Using Matplotlib, create a thumbnail sized plot of the waveform data and save
        it to a bytes IO object provided as a parameter to this function
        """
        thumbnail_size = Config.config.waveforms.thumbnail_size
        # 1 in figsize = 100px
        plt.figure(figsize=(thumbnail_size[0] / 100, thumbnail_size[1] / 100))
        # Removes the notches on the plot that provide a scale
        plt.xticks([])
        plt.yticks([])
        # Line width is configurable - thickness of line in the waveform
        plt.plot(
            self.waveform.x,
            self.waveform.y,
            linewidth=Config.config.waveforms.line_width,
        )
        # Disables all axis decorations
        plt.axis("off")
        # Removes the frame around the plot
        plt.box(False)

        # Setting bbox_inches="tight" and pad_inches=0 removes padding around figure
        # to make best use of the limited pixels available in a thumbnail. Because of
        # this, dpi has been set to 130 to offset the tight bbox removing white space
        # around the figure and there keeps the thumbnail size calculation correct. The
        # default dpi is 100 but that will result in thumbnails smaller than the
        # configuration setting, hence the value of 130
        plt.savefig(buffer, format="PNG", bbox_inches="tight", pad_inches=0, dpi=130)
        # Flushes the plot to remove data from previously ingested waveforms
        plt.clf()
        plt.close()

    def _create_fullsize_plot(self, buffer, x_label, y_label) -> None:
        """
        Using Matplotlib, create a full sized plot of the waveform data and save it to
        a bytes IO object provided as a parameter to this function
        """
        plt.figure(figsize=(8, 6))
        plt.plot(
            self.waveform.x,
            self.waveform.y,
        )
        plt.xlabel(x_label)
        plt.ylabel(y_label)

        plt.savefig(buffer, format="PNG", bbox_inches="tight", pad_inches=0.1, dpi=130)
        # Flushes the plot to remove data from previously ingested waveforms
        plt.clf()

    @staticmethod
    def get_relative_path(record_id: str, channel_name: str) -> str:
        """
        Returns a relative waveform path given a record ID and channel name. The path is
        relative to the base directory of where waveforms are stored in Echo
        """
        return f"{record_id}/{channel_name}.json"

    @staticmethod
    def get_full_path(relative_path: str) -> str:
        """
        Converts a relative waveform path to a full path by adding the 'prefix' onto a
        relative path of a waveform. The full path doesn't include the bucket name
        """
        return f"{Waveform.echo_prefix}/{relative_path}"

    @staticmethod
    def get_waveform(waveform_path: str) -> WaveformModel:
        """
        Given a waveform path, find the waveform from Echo. This function assumes that
        the waveform should exist; if no waveform can be found, a `WaveformError` will
        be raised
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

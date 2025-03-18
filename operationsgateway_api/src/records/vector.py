import base64
from io import BytesIO
import json
import logging

from botocore.exceptions import ClientError
from matplotlib import pyplot as plt

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import (
    EchoS3Error,
    VectorError,
)
from operationsgateway_api.src.models import VectorModel
from operationsgateway_api.src.records.echo_interface import EchoInterface


log = logging.getLogger()


class Vector:
    echo_prefix = "vectors"

    def __init__(self, vector: VectorModel) -> None:
        self.vector = vector
        self.thumbnail = None

    @staticmethod
    async def get_vector(record_id: str, channel_name: str) -> VectorModel:
        """
        Get vector data from storage and return it as a VectorModel. If no vector can be
        found, a VectorError will be raised.
        """
        log.info("Retrieving vector and returning a VectorModel")
        echo = EchoInterface()

        try:
            relative_path = Vector.get_relative_path(record_id, channel_name)
            full_path = Vector.get_full_path(relative_path)
            bytes_io = echo.download_file_object(full_path)
            vector_dict = json.loads(bytes_io.getvalue().decode())
            return VectorModel(**vector_dict)
        except (ClientError, EchoS3Error) as exc:
            log.error("Vector could not be found: %s", relative_path)
            msg = f"Vector could not be found on object storage: {relative_path}"
            raise VectorError(msg) from exc

    @staticmethod
    def get_relative_path(
        record_id: str,
        channel_name: str,
        use_subdirectories: bool = True,
    ) -> str:
        """
        Returns a relative path given a record id and channel name. The path is relative
        to the base directory.
        """
        directories = EchoInterface.format_record_id(record_id, use_subdirectories)
        return f"{directories}/{channel_name}.json"

    @staticmethod
    def get_full_path(relative_path: str) -> str:
        """
        Returns the full path by adding the storage base directory to the start of the
        path. The full path does not include the bucket name.
        """
        return f"{Vector.echo_prefix}/{relative_path}"

    def get_channel_name_from_path(self) -> str:
        """
        Get the channel name from the storage path.
        """
        return self.vector.path.split("/")[-1].split(".json")[0]

    def insert(self) -> str | None:
        """
        Upload the bytes of this vector to storage. Returns the channel name if the
        upload fails.
        """
        log.info("Storing vector: %s", self.vector.path)
        echo = EchoInterface()
        try:
            bytes_io = BytesIO(self.vector.model_dump_json(indent=2).encode())
            echo.upload_file_object(bytes_io, Vector.get_full_path(self.vector.path))
            return  # Successful upload
        except EchoS3Error:
            # Extract the channel name and propagate it
            channel_name = self.get_channel_name_from_path()
            log.exception("Failed to upload vector for channel '%s'", channel_name)
            return channel_name

    def create_thumbnail(self) -> None:
        """
        Create a thumbnail of the vector data and store it in this object.
        """
        with BytesIO() as bytes_io:
            thumbnail_size = Config.config.vectors.thumbnail_size
            # 1 in figsize = 100px
            plt.figure(figsize=(thumbnail_size[0] / 100, thumbnail_size[1] / 100))
            plt.xticks([])
            plt.yticks([])
            plt.bar(range(len(self.vector.data)), self.vector.data)
            plt.axis("off")
            plt.axhline(c="black")
            plt.box(False)
            plt.savefig(
                bytes_io,
                format="PNG",
                bbox_inches="tight",
                pad_inches=0,
                dpi=130,
            )
            plt.clf()
            plt.close()
            self.thumbnail = base64.b64encode(bytes_io.getvalue())

    def get_fullsize_png(self, labels: list[str] | None) -> bytes:
        """
        Create a full size image of the vector data and return it.
        """
        if not labels:
            labels = range(len(self.vector.data))

        with BytesIO() as bytes_io:
            plt.figure(figsize=(8, 6))
            plt.bar(labels, self.vector.data)
            plt.savefig(
                bytes_io,
                format="PNG",
                bbox_inches="tight",
                pad_inches=0.1,
                dpi=130,
            )
            plt.clf()
            return bytes_io.getvalue()

import base64
from io import BytesIO
import json
import logging

from matplotlib import pyplot as plt

from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import EchoS3Error
from operationsgateway_api.src.models import VectorModel
from operationsgateway_api.src.records.channel_object_abc import ChannelObjectABC
from operationsgateway_api.src.records.echo_interface import get_echo_interface
from operationsgateway_api.src.users.preferences import UserPreferences


log = logging.getLogger()


class Vector(ChannelObjectABC):
    echo_prefix = "vectors"
    echo_extension = "json"

    def __init__(self, vector: VectorModel) -> None:
        self.vector = vector
        self.thumbnail = None

    @staticmethod
    async def get_vector(record_id: str, channel_name: str) -> VectorModel:
        """
        Get vector data from storage and return it as a VectorModel. If no vector can be
        found, an Exception will be raised.
        """
        log.info("Retrieving vector and returning a VectorModel")
        bytes_io = await Vector.get_bytes(
            record_id=record_id,
            channel_name=channel_name,
        )
        vector_dict = json.loads(bytes_io.getvalue().decode())
        return VectorModel(**vector_dict)

    @staticmethod
    async def get_skip_limit(access_token: str) -> tuple[int | None, int | None]:
        """
        Check the user's database record to see if they have a preferred skip and/or
        limit on the entries to display.
        """
        username = JwtHandler.get_payload(access_token)["username"]
        skip = await UserPreferences.get_default(
            username,
            Config.config.vectors.skip_pref_name,
            enforce_type=int,
        )
        limit = await UserPreferences.get_default(
            username,
            Config.config.vectors.limit_pref_name,
            enforce_type=int,
        )

        msg = "Preferred vector skip, limit for %s is %s, %s"
        log.debug(msg, username, skip, limit)
        return skip, limit

    def get_channel_name_from_path(self) -> str:
        """
        Get the channel name from the storage path.
        """
        return self.vector.path.split("/")[-1].split(".json")[0]

    async def insert(self) -> str | None:
        """
        Upload the bytes of this vector to storage. Returns the channel name if the
        upload fails.
        """
        log.info("Storing vector: %s", self.vector.path)
        echo_interface = get_echo_interface()
        try:
            bytes_io = BytesIO(self.vector.model_dump_json(indent=2).encode())
            full_path = Vector.get_full_path(self.vector.path)
            await echo_interface.upload_file_object(bytes_io, full_path)
            return  # Successful upload
        except EchoS3Error:
            # Extract the channel name and propagate it
            channel_name = self.get_channel_name_from_path()
            log.exception("Failed to upload vector for channel '%s'", channel_name)
            get_echo_interface.cache_clear()  # Invalidate the cache as a precaution
            return channel_name

    def create_thumbnail(
        self,
        skip: int | None = None,
        limit: int | None = None,
    ) -> None:
        """
        Create a thumbnail of the vector data and store it in this object.
        """
        data = self.vector.data[skip:limit]
        with BytesIO() as bytes_io:
            thumbnail_size = Config.config.vectors.thumbnail_size
            # 1 in figsize = 100px
            plt.figure(figsize=(thumbnail_size[0] / 100, thumbnail_size[1] / 100))
            plt.xticks([])
            plt.yticks([])
            plt.bar(range(len(data)), data)
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

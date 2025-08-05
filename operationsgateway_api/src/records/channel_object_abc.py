from abc import ABC, abstractmethod
from io import BytesIO
import logging

from operationsgateway_api.src.exceptions import EchoS3Error
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.echo_interface import (
    EchoInterface,
    get_echo_interface,
)


log = logging.getLogger()


class ChannelObjectABC(ABC):

    @property
    @abstractmethod
    def echo_prefix(self) -> str: ...

    @property
    @abstractmethod
    def echo_extension(self) -> str: ...

    @classmethod
    def get_relative_path(
        cls,
        record_id: str,
        channel_name: str,
        use_subdirectories: bool = True,
    ) -> str:
        """
        Returns a relative path given a record ID and channel name. The path is relative
        to the base directory of where objects of this type are stored in Echo.
        """
        directories = EchoInterface.format_record_id(record_id, use_subdirectories)
        return f"{directories}/{channel_name}.{cls.echo_extension}"

    @classmethod
    def get_full_path(cls, relative_path: str) -> str:
        """
        Converts a relative path to a full path by adding the 'prefix' onto a relative
        path. The full path doesn't include the bucket name.
        """
        return f"{cls.echo_prefix}/{relative_path}"

    @classmethod
    async def get_bytes(
        cls,
        record_id: str,
        channel_name: str,
        use_subdirectories: bool = True,
    ) -> BytesIO:
        """
        Gets the bytes for this record and channel, handling any exceptions.
        """
        echo_interface = get_echo_interface()
        try:
            relative_path = cls.get_relative_path(
                record_id=record_id,
                channel_name=channel_name,
                use_subdirectories=use_subdirectories,
            )
            full_path = cls.get_full_path(relative_path)
            return await echo_interface.download_file_object(full_path)
        except EchoS3Error as exc:
            if use_subdirectories:
                return await cls.get_bytes(
                    record_id=record_id,
                    channel_name=channel_name,
                    use_subdirectories=False,
                )
            else:
                await cls.handle_exception(
                    record_id=record_id,
                    channel_name=channel_name,
                    exc=exc,
                )

    @classmethod
    async def handle_exception(
        cls,
        record_id: str,
        channel_name: str,
        exc: EchoS3Error,
    ) -> None:
        """
        Log and raise an exception with an appropriate message/code depending on
        whether the data is only missing in Echo, or from Mongo as well.
        """
        filter_ = {"_id": record_id, f"channels.{channel_name}": {"$exists": True}}
        record_count = await MongoDBInterface.count_documents("records", filter_)
        if record_count == 0:
            msg = (
                f"{cls.__name__} with id={record_id}, channel={channel_name} "
                "could not be found due to invalid id and or channel"
            )
            log.error(msg)
            raise EchoS3Error(msg=msg, status_code=404) from exc
        elif record_count == 1:
            msg = (
                f"{cls.__name__} with id={record_id}, channel={channel_name} "
                "could not be found in object storage, check deletion policy and age "
                "of requested data"
            )
            log.error(msg)
            raise EchoS3Error(msg=msg, status_code=404) from exc
        else:
            get_echo_interface.cache_clear()  # Invalidate the cache as a precaution
            msg = (
                f"Unexpected number of records ({record_count}) found when verifying "
                f"whether {record_id}, {channel_name} should be available on object "
                "storage"
            )
            log.error(msg)
            raise EchoS3Error(msg, status_code=500) from exc

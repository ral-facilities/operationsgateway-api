import logging

from operationsgateway_api.src.models import TagModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.routes.common_parameters import ParameterHandler

log = logging.getLogger()


class Tag:
    @staticmethod
    async def get_all_tags_from_database() -> list[TagModel]:
        """
        Get every tag, ordered by name. Tags which have been retired have `active` set
        to false, they are still returned so records that have them can be found. A tag
        without an `active` field is treated as retired. The list is empty if there are
        no tags in the database, including if the `tags` collection has not been
        created.
        """

        tags_query = MongoDBInterface.find(
            "tags",
            sort=ParameterHandler.extract_order_data(["name asc"]),
        )
        tags = await MongoDBInterface.query_to_list(tags_query)

        return [
            TagModel(
                name=tag["name"],
                description=tag.get("description", ""),
                active=tag.get("active", False),
            )
            for tag in tags
        ]

    @staticmethod
    async def get_active_tags_from_database() -> list[TagModel]:
        """
        Get the tags that can currently be used, ordered by name. Tags which have been
        retired (`active` is false) are not returned. This is the controlled vocabulary
        that tags in ingested HDF files are validated against.
        """

        return [tag for tag in await Tag.get_all_tags_from_database() if tag.active]

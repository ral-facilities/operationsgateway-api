import logging

from operationsgateway_api.src.models import TagModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.routes.common_parameters import ParameterHandler

log = logging.getLogger()


class Tag:
    @staticmethod
    async def get_active_tags_from_database() -> list[TagModel]:
        """
        Get the tags that can currently be used, ordered by name.
        Tags which have been retired (`active` is false) are not returned. The list is
        empty if there are no tags in the database, including if the `tags` collection
        has not been created.
        """

        tags_query = MongoDBInterface.find(
            "tags",
            filter_={"active": True},
            sort=ParameterHandler.extract_order_data(["name asc"]),
        )
        tags = await MongoDBInterface.query_to_list(tags_query)

        return [
            TagModel(name=tag["name"], description=tag.get("description", ""))
            for tag in tags
        ]

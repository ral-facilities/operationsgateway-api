import logging

from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.models import RecordModel


log = logging.getLogger()


class IngestionValidator:
    def __init__(self, ingested_record: RecordModel, stored_record: RecordModel):
        self.ingested_record = ingested_record
        self.stored_record = stored_record

    def search_existing_data(self):
        """
        Search through the existing record stored in MongoDB to see if any fields exist
        in the data extracted from the HDF file

        Current check ideas (pending full list from CLF):
        - How do you deal with situations where the input record could overwrite
        something that's already stored in the database (same channel for a particular
        record ID in both ingested and stored record)? This would be the place to reject
        the file if we don't want to let that happen
        """
        pass

    async def validate_against_manifest(self):
        """
        Current check ideas (pending full list from CLF):
        - Where units in the record are different to what's in the manifest file, reject
        the file. If no units then skip the check
        - Should we be ingesting channels that the manifest file says is historical?
        - Should we be ingesting channels that don't exist in the manifest file?

        Do each check and as soon as one fails, return False so you could do something
        with the break statement
        """

        # Get manifest file to use it in the checks
        channel_manifest = await ChannelManifest.get_most_recent_manifest()
        # To satisfy F841 from flake8 before this functionality is implemented
        channel_manifest

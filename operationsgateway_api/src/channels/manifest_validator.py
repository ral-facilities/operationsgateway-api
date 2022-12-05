import logging

from operationsgateway_api.src.exceptions import ApiError, ChannelManifestError
from operationsgateway_api.src.models import ChannelManifestModel, ChannelModel


log = logging.getLogger()


class ManifestValidator:
    def __init__(
        self,
        input_file: ChannelManifestModel,
        stored_file: ChannelManifestModel,
        bypass_channel_check: bool,
    ) -> None:
        self.input_file = input_file
        self.stored_file = stored_file
        self.bypass_channel_check = bypass_channel_check

    def perform_validation(self) -> None:
        """
        Function to run each step of the validation proces
        """

        if not self.bypass_channel_check:
            self._check_removed_channels()
        self._check_modified_metadata()

    def _check_removed_channels(self) -> None:
        """
        Check whether data channels have been removed from the manifest file submitted
        by the user. If so, raise a `ChannelManifestError` which will provide a 400
        response to the user
        """

        for channel_name in self.stored_file.channels.keys():
            try:
                self.input_file.channels[channel_name]
            except KeyError as exc:
                raise ChannelManifestError(
                    f"{channel_name} has been removed from the input channel metadata."
                    " Channels cannot be removed, add the channel back into the file"
                    " and re-submit",
                ) from exc

    def _check_modified_metadata(self) -> None:
        """
        For protected fields, check whether they've been modified and return a 400 (by
        raising a `ChannelManifestError` if that's the case.

        There's some defensiveness in this function by ensuring the channel names match
        up. In practice they should be the same but this could be a strange bug that
        with some defensive code, will be much easier to diagnose
        """

        for (input_channel_name, input_metadata), (
            stored_channel_name,
            stored_metadata,
        ) in zip(self.input_file.channels.items(), self.stored_file.channels.items()):
            if not input_channel_name == stored_channel_name:
                log.debug(
                    "Input channel name: %s, Stored channel name: %s",
                    input_channel_name,
                    stored_channel_name,
                )
                raise ApiError(
                    "Input and stored channel names for manifest validation not the"
                    " same",
                )

            for field_name in ChannelModel.protected_fields:
                if getattr(input_metadata, field_name) != getattr(
                    stored_metadata,
                    field_name,
                ):
                    raise ChannelManifestError(
                        f"{field_name} has been modified on the {input_channel_name}"
                        " channel. Value stored in database:"
                        f" {getattr(stored_metadata, field_name)}. Re-submit the"
                        " channel metadata without the modification. If the metadata"
                        " must be changed, please create a new channel.",
                    )

import logging

from operationsgateway_api.src.exceptions import RejectFileError
from operationsgateway_api.src.models import RecordModel


class FileChecks:
    def __init__(self, ingested_record: RecordModel):
        """
        This class is instantiated using the RecordModel from running hdf_handler
        """
        self.ingested_record = ingested_record

    def epac_data_version_checks(self):
        """
        Checks that the epac_data_version on the file is "1.0"
        if:
            it is not a string = a file error is raised
            the first number is not "1" = a file error is raised
            the second number is not "0" = a warning is given
        """
        ingested_metadata = (self.ingested_record).metadata
        if (
            hasattr(ingested_metadata, "epac_ops_data_version")
            and ingested_metadata.epac_ops_data_version is not None
        ):
            epac_number = ingested_metadata.epac_ops_data_version
            if type(ingested_metadata.epac_ops_data_version) != str:
                raise RejectFileError(
                    "epac_ops_data_version has wrong datatype. Should be string",
                )
            else:
                epac_numbers = epac_number.split(".")
                if epac_numbers[0] != "1":
                    raise RejectFileError(
                        "epac_ops_data_version major version was not 1",
                    )
                if int(epac_numbers[1]) > 0:
                    return "File minor version number too high (expected 0)"
        else:
            raise RejectFileError("epac_ops_data_version does not exist")
        # a RecordMetadataModel is already returned when
        # epac_ops_data_version does not exist

from pathlib import Path

# a dictionary used by the authorisation system to map endpoint functions to endpoint
# "path" and "method" values, for example:
# <function get_full_image at 0x7f171d7039d0>, '/images/{record_id}/{channel_name} GET'
ROUTE_MAPPINGS = {}

ID_DATETIME_FORMAT = "%Y%m%d%H%M%S"
DATA_DATETIME_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%f%z",  # with fractional seconds (1–6 digits)
    "%Y-%m-%dT%H:%M:%S%z",     # without fractional seconds
]
MANIFEST_DATETIME_FORMAT = "%Y%m%d%H%M%S"
SESSION_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

LOG_CONFIG_LOCATION = str(Path(__file__).parent.parent / "logging.ini")

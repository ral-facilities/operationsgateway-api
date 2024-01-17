from pathlib import Path

# a dictionary used by the authorisation system to map endpoint functions to endpoint
# "path" and "method" values, for example:
# <function get_full_image at 0x7f171d7039d0>, '/images/{record_id}/{channel_name} GET'
ROUTE_MAPPINGS = {}
ID_DATETIME_FORMAT = "%Y%m%d%H%M%S"
DATA_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_CONFIG_LOCATION = str(Path(__file__).parent.parent / "logging.ini")
ECHO_IMAGES_PREFIX = "images"

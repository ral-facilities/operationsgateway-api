import argparse
import base64
import hashlib

"""
This script is used to generate MD5 checksums, used to assert thumbnails in tests
"""

parser = argparse.ArgumentParser()
parser.add_argument(
    "-t",
    "--thumbnail",
    type=str,
    help="Base 64 version of the thumbnail",
    required=True,
)

# Put command line options into variables
args = parser.parse_args()
BASE64_THUMBNAIL = args.thumbnail

bytes_thumbnail = base64.b64decode(BASE64_THUMBNAIL)
md5_checksum = hashlib.md5(bytes_thumbnail).hexdigest()

print(f"MD5 Checksum: {md5_checksum}")

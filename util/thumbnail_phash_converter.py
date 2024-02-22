import argparse
import base64
import io

import imagehash
from PIL import Image

"""
This script is used to generate perceptual hashes, used to assert thumbnails in tests
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
image = Image.open(io.BytesIO(bytes_thumbnail))
phash = imagehash.phash(image)

print(f"Perceptual hash: {phash}")

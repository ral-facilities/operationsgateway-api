import sys

from operationsgateway_api.src.config import Config

# Read the contents of the private and public key files into constants.
# These are used for encoding and decoding of JWT access and refresh tokens for
# authentication.
try:
    with open(Config.config.auth.private_key_path, "r") as f:
        PRIVATE_KEY = f.read()
except FileNotFoundError as exc:
    sys.exit(f"Cannot find private key: {exc}")

try:
    with open(Config.config.auth.public_key_path, "r") as f:
        PUBLIC_KEY = f.read()
except FileNotFoundError as exc:
    sys.exit(f"Cannot find public key: {exc}")

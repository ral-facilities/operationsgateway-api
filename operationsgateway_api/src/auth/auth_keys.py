import sys

from operationsgateway_api.src.config import Config

# Read the contents of the private and public key files into constants.
# These are used for encoding and decoding of JWT access and refresh tokens for
# authentication.


def get_private_key():
    path = Config.config.auth.private_key_path
    try:
        with open(path, "r") as f:
            private_key = f.read()
            return private_key
    except FileNotFoundError as exc:
        sys.exit(f"Cannot find private key: {exc}")


def get_public_key():
    path = Config.config.auth.public_key_path
    try:
        with open(path, "r") as f:
            public_key = f.read()
            return public_key
    except FileNotFoundError as exc:
        sys.exit(f"Cannot find public key: {exc}")

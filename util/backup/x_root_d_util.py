import argparse
from typing import Literal

from operationsgateway_api.src.backup.x_root_d_client import XRootDClient


def main(action: Literal["backup", "restore"], source: str) -> None:
    if action == "backup":
        XRootDClient.backup(source_top=source)
    elif action == "restore":
        XRootDClient.restore(source_top=source)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=["backup", "restore"],
        help="Action to perform",
        required=True,
    )
    parser.add_argument(
        "source",
        type=str,
        help=(
            "Source path, including the server address if restoring. "
            "Directories will be walked to find all nested files."
        ),
        required=True,
    )

    args = parser.parse_args()
    main(action=args.action, source=args.source)

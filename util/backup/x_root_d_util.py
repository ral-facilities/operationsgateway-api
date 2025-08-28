import argparse
import logging
import os

from operationsgateway_api.src.backup.x_root_d_client import XRootDClient


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "url",
        help=(
            "Url for remote XRootD server including top level directory path, "
            "for example root://hostname.domain:1094//path/to/directory"
        ),
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Increase logging level to DEBUG.",
    )
    sub_parsers = parser.add_subparsers(required=True, dest="subcommand")

    backup_parser = sub_parsers.add_parser(
        "backup",
        help="Backup files in local directory to tape.",
    )
    backup_parser.add_argument(
        "source",
        type=str,
        help="Local source path. Directories will be walked to find all nested files.",
    )

    restore_parser = sub_parsers.add_parser(
        "restore",
        help="Restore files in a remote directory to tape",
    )
    restore_parser.add_argument(
        "source",
        type=str,
        help=(
            "Remote relative source path. "
            "Directories will be walked to find all nested files."
        ),
    )
    restore_parser.add_argument(
        "target",
        type=str,
        help="Local directory to restore relative paths to.",
    )

    args = parser.parse_args()

    stream_handler = logging.StreamHandler()
    if args.verbose:
        stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(logging.Formatter("%(levelname)8s : %(message)s"))
    logging.basicConfig(level=logging.DEBUG, handlers=[stream_handler])

    x_root_d_client = XRootDClient(args.url)
    if args.subcommand == "backup":
        x_root_d_client.backup(source_top=os.path.abspath(args.source))
    elif args.subcommand == "restore":
        target_top = os.path.abspath(args.target)
        x_root_d_client.restore(source_top=args.source, target_top=target_top)
    else:
        raise ValueError(f"Unrecognized subcommand {args.subcommand}")

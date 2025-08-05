import os
from typing import Generator

from XRootD.client import CopyProcess, FileSystem, URL

from operationsgateway_api.src.backup.x_root_d_progress_handler import (
    XRootDProgressHandler,
)
from operationsgateway_api.src.config import Config


class XRootDClient:
    @staticmethod
    def backup(source_top: str) -> None:
        """
        Creates and runs a CopyProcess for all files within source_top to backup
        storage.
        """
        copy_process = CopyProcess()
        for dirpath, _dirnames, filenames in os.walk(source_top):
            for filename in filenames:
                source = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(
                    path=source,
                    start=Config.config.backup.cache_directory,
                )
                relative_path = relative_path[relative_path.index("/") + 1 :]
                target_url = str(Config.config.backup.target_url)
                target = os.path.join(target_url, relative_path)
                copy_process.add_job(
                    source=source,
                    target=target,
                    mkdir=True,
                )

        copy_process.prepare()
        copy_process.run(handler=XRootDProgressHandler())

    @staticmethod
    def _dirlist(file_system: FileSystem, path: str) -> Generator[str, None, None]:
        """
        Recursively list all files on a remote XRootD server.
        """
        status, directory_list = file_system.dirlist(path)
        for entry in directory_list:
            full_path = os.path.join(path, entry)
            if entry.endswith(".hdf5"):
                yield full_path
            else:
                for filepath in XRootDClient._dirlist(full_path):
                    yield filepath

    @staticmethod
    def restore(source_top: str, target_top: str) -> None:
        """
        Creates and runs a CopyProcess for all files within source_top from backup
        storage to target_top on local storage.
        """
        copy_process = CopyProcess()
        url = URL(Config.config.backup.target_url)
        file_system = FileSystem(url.hostid)
        path = os.path.join(url.path, source_top)
        for filepath in XRootDClient._dirlist(file_system=file_system, path=path):
            relative_path = os.path.relpath(path=filepath, start=url.path)
            source = os.path.join(Config.config.backup.target_url, relative_path)
            target = os.path.join(target_top, relative_path)
            copy_process.add_job(
                source=source,
                target=target,
                mkdir=True,
            )

        copy_process.prepare()
        copy_process.run(handler=XRootDProgressHandler())

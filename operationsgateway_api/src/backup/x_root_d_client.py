import json
import logging
import os
from time import sleep
from typing import Generator

from XRootD.client import CopyProcess, FileSystem, URL
from XRootD.client.flags import DirListFlags, PrepareFlags, QueryCode, StatInfoFlags

from operationsgateway_api.src.backup.x_root_d_backup_handler import (
    XRootDBackupHandler,
)
from operationsgateway_api.src.backup.x_root_d_restore_handler import (
    XRootDRestoreHandler,
)


log = logging.getLogger(__name__)


class XRootDClient:

    def __init__(self, url_str: str):
        self.url = URL(url_str)
        self.file_system = FileSystem(self.url.hostid)

    def backup(self, source_top: str) -> None:
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
                    start=source_top,
                )
                remote_path = os.path.join(self.url.path, relative_path)
                status, stat_info = self.file_system.stat(remote_path)
                if status.ok:
                    log.warning("File %s already archived, skipping", relative_path)
                elif status.errno == 3011:  # No such file of directory, so archive it
                    copy_process.add_job(
                        source=source,
                        target=os.path.join(str(self.url), relative_path),
                        mkdir=True,
                    )
                else:
                    log.error("Stat failed with %s", status.message)

        log.info("Starting copy")
        copy_process.prepare()
        copy_process.run(handler=XRootDBackupHandler())

    def restore(self, source_top: str, target_top: str) -> None:
        """
        Creates and runs a CopyProcess for all files within source_top from backup
        storage to target_top on local storage.
        """
        path = os.path.join(self.url.path, source_top)
        file_dict = {}
        for filepath in self._dirlist(path=path):
            relative_path = os.path.relpath(path=filepath, start=self.url.path)
            source = os.path.join(str(self.url), relative_path)
            source_path_only = os.path.join(self.url.path, relative_path)
            target = os.path.join(target_top, relative_path)
            file_dict[source_path_only] = {"source": source, "target": target}

        files = list(file_dict.keys())
        status, response = self.file_system.prepare(files, flags=PrepareFlags.STAGE)

        if status.ok:
            request_id = response.strip(b"\x00").decode()
            copy_process = CopyProcess()
            self._extract_online(file_dict, request_id, copy_process)
            while len(file_dict) > 0:
                self._extract_online(file_dict, request_id, copy_process)

            log.info("All files prepared, starting copy")
            copy_process.prepare()
            copy_process.run(handler=XRootDRestoreHandler(file_system=self.file_system))
        else:
            log.error("Prepare failed with: %s", status.message)

    def _dirlist(self, path: str, extension: str = None) -> Generator[str, None, None]:
        """
        Recursively list all files on a remote XRootD server.
        """
        status, directory_list = self.file_system.dirlist(path, DirListFlags.STAT)
        if directory_list is None:
            # Might be a complete path to a file not a directory
            status, stat_info = self.file_system.stat(path)
            if status.ok:
                if not stat_info.flags & StatInfoFlags.IS_DIR:
                    yield path
        else:
            # Iterate over contents of the directory
            for entry in directory_list:
                full_path = os.path.join(path, entry.name)
                if entry.statinfo.flags & StatInfoFlags.IS_DIR:
                    for filepath in self._dirlist(full_path):
                        yield filepath
                elif extension is None or entry.name.endswith(extension):
                    yield full_path

    def _extract_online(
        self,
        file_dict: dict[str, str],
        request_id: str,
        copy_process: CopyProcess,
        sleep_seconds: float = 1,
    ) -> None:
        """
        Use `file_system` to stat which files in `file_dict` are online, and add these
        to the `copy_process`.
        """
        n_files = len(file_dict)
        log.info("Waiting %s for %s files to be prepared", sleep_seconds, n_files)
        sleep(sleep_seconds)
        query = "\n".join(file_dict.keys())
        arg = f"{request_id}\n{query}"
        status, response = self.file_system.query(QueryCode.PREPARE, arg)
        if status.ok:
            response_dict = json.loads(response)
            for file_response in response_dict["responses"]:
                path = file_response["path"]
                error_text = file_response["error_text"]
                if error_text:
                    log.warning("File %s had error: %s", path, error_text)
                    file_dict.pop(path)
                elif not file_response["path_exists"]:
                    log.warning("File %s does not exist", path)
                    file_dict.pop(path)
                elif file_response["online"]:
                    log.debug("File %s online", path)
                    file_entry = file_dict.pop(path)
                    copy_process.add_job(
                        source=file_entry["source"],
                        target=file_entry["target"],
                        mkdir=True,
                    )
                elif not file_response["requested"] or not file_response["has_reqid"]:
                    log.warning("File %s not requested for staging", path)
                    file_dict.pop(path)

        else:
            log.error("Query failed with: %s", status.message)

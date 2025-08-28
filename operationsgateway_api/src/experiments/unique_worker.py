from functools import wraps
import logging
import os
from pathlib import Path

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import ApiError


log = logging.getLogger()


class UniqueWorker:
    """
    Where multiple workers are launched for this API (by uvicorn for example), this
    class is used to assign a task to a single worker. For example, the background task
    to contact the Scheduler on a regular basis only needs to be performed by a single
    worker. The worker chosen to perform the task (i.e. the 'assigned worker') is
    selected by checking whether a particular file is empty or not. If the object finds
    an empty file, it becomes the assigned worker and writes its process ID to the file.

    The decorator (not in this class but at the bottom of this file) checks the contents
    of the file (looking to match the process ID in the file with the process ID of the
    worker) as a 'double check' to prevent race conditions.
    """

    def __init__(self, worker_file_path: str) -> None:
        self.id_ = str(os.getpid())
        self.worker_file_path = Path(worker_file_path)
        self.file_empty = self._is_file_empty()
        log.debug(
            "File empty for PID %s: %s",
            self.id_,
            self.file_empty,
        )
        if self.file_empty:
            log.debug("Assigning PID to current object: %s", self.id_)
            self._assign()
            self.is_assigned = True
        else:
            self.is_assigned = False

    def does_pid_match_file(self) -> bool:
        """
        Check to see if the process ID stored in the file matches the process ID that
        the object is assigned to
        """
        pid = self._read_file()
        return True if self.id_ == pid else False

    def remove_file(self) -> None:
        try:
            log.debug("Worker file attempting to be deleted: %s", self.worker_file_path)
            os.remove(self.worker_file_path)
        except FileNotFoundError:
            # If the file doesn't exist, that's ok as the file cannot be deleted if it
            # doesn't exist
            pass

    def _is_file_empty(self) -> bool:
        """
        Check if the file is empty, returning a boolean result. If the file cannot be
        found, create the file and assume it is empty when returning
        """

        try:
            pid = self._read_file()
            log.debug("File contents for PID %s: %s", self.id_, pid)
            return False if pid else True
        except FileNotFoundError:
            # Create file (including path to it)
            msg = "Worker file doesn't exist, going to create one at: %s"
            log.debug(msg, self.worker_file_path)
            self.worker_file_path.parents[0].mkdir(parents=True, exist_ok=True)
            return True

    def _assign(self) -> None:
        """
        'Assign' the event to the PID by writing the PID to the file
        """
        try:
            with open(self.worker_file_path, "w") as f:
                f.write(self.id_)
                log.info("Worker assigned to PID: %s", self.id_)
        except OSError as exc:
            raise ApiError(f"Cannot open PID file: {self.worker_file_path}") from exc

    def _read_file(self) -> str:
        with open(self.worker_file_path, "r") as f:
            output = f.read()

        return output


def assign_event_to_single_worker(unique_worker: UniqueWorker):
    """
    This decorator ensures that an event that it's applied to only executed by a single
    worker rather than each worker part of the FastAPI app
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # When the reloader option is enabled, comparing the PID in the file isn't
            # reliable. This is because the process that writes in the file becomes the
            # reloader process and doesn't act as an API process so that process doesn't
            # execute this decorator, thereby never executing the event. Checking an
            # `is_assigned` attribute is more reliable when reloading files is enabled
            # but less reliable when that option is disabled (some kind of race
            # condition could occur). The reload option is only enabled for development
            # purposes so the more reliable check (i.e. matching the PID in the file) is
            # performed in production
            if Config.config.app.reload:
                if not unique_worker.is_assigned:
                    log.debug(
                        "Worker isn't assigned to this event, PID: %s. Reload enabled",
                        unique_worker.id_,
                    )
                    return
            else:
                if not unique_worker.does_pid_match_file():
                    log.debug(
                        "PID doesn't match that of the worker (%s). Reload disabled",
                        unique_worker.id_,
                    )
                    return

            log.info("Event will be executed by PID: %s", unique_worker.id_)
            return await func(*args, **kwargs)

        return wrapper

    return decorator

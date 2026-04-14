from abc import ABC, abstractmethod
import asyncio
from copy import copy
from datetime import datetime
import logging

from cron_converter import Cron
from dateutil import tz

log = logging.getLogger()


class RunnerABC(ABC):
    """
    ABC for tasks that need to regularly run with frequency controlled by a cron string.
    """

    def __init__(self, task_name: str, cron_string: str, timezone_str: str) -> None:
        self.task_name = task_name
        self.timezone_str = timezone_str
        cron = Cron(cron_string)
        self.runner_dates = cron.schedule(timezone_str=timezone_str)

    def get_next_run_task_date(self) -> datetime:
        """
        Make a copy of the task running dates and return the datetime of the next one.
        This is done so client code knows when the next task will be executed
        """
        runner_dates_copy = copy(self.runner_dates)
        return runner_dates_copy.next()

    def _get_wait_interval(self) -> float:
        """
        Get the next run date and calculate the number of seconds between the current
        datetime and when the next run date is
        """
        scheduled_run = self.runner_dates.next()
        log.info(
            "Next scheduled run of background task (%s): %s",
            self.task_name,
            scheduled_run,
        )
        timezone = tz.gettz(self.timezone_str)
        current_date = datetime.now(tz=timezone)

        wait_time = (scheduled_run - current_date).total_seconds()
        log.debug(
            "Number of seconds between now and next task run (%s): %d",
            self.task_name,
            wait_time,
        )
        return wait_time

    async def start_task(self) -> None:
        """
        Start the task and keep it running by iterating through `while True`.
        Async sleeps are used as a way to wait until the next task should occur.
        """
        while True:
            await asyncio.sleep(self._get_wait_interval())
            await self.run_task()

    @abstractmethod
    async def run_task(self) -> None: ...

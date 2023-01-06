import logging

import asyncio

from operationsgateway_api.src.config import Config

log = logging.getLogger()


class BackgroundSchedulerRunner:
    def __init__(self) -> None:
        pass

    def _get_task_frequency(self) -> int:
        task_interval = Config.config.experiments.get_experiments_frequency_minutes * 60
        log.debug("Number of seconds between tasks: %d", task_interval)
        return task_interval

    async def start_task(self) -> None:
        while True:
            print("Starting scheduler task")
            # START HERE

            await asyncio.sleep(self._get_task_frequency())
            log.info("Contact scheduler in background")

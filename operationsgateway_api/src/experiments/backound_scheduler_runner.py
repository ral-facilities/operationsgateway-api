from datetime import datetime
from dateutil import tz
import logging
import asyncio

from cron_converter import Cron

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.experiments.experiment import Experiment

log = logging.getLogger()


class BackgroundSchedulerRunner:
    def __init__(self, task_name: str) -> None:
        self.task_name = task_name
        self.runner_timer = Cron(
            Config.config.experiments.scheduler_background_frequency,
        )

        # TODO - ValueError raised if invalid timezone is given
        self.runner_dates = self.runner_timer.schedule(
            timezone_str=Config.config.experiments.scheduler_background_timezone,
        )
    
    def _get_wait_interval(self) -> float:
        scheduled_run = self.runner_dates.next()
        log.info(
            "Next scheduled run of background task (%s): %s",
            self.task_name,
            scheduled_run,
        )
        # TODO - if current_date.tzinfo, timezone wasn't recognised. Raise exception?
        timezone = tz.gettz(Config.config.experiments.scheduler_background_timezone)
        current_date = datetime.now(tz=timezone)

        wait_time = (scheduled_run-current_date).total_seconds()
        log.debug(
            "Number of seconds between now and next task run (%s): %d",
            self.task_name,
            wait_time,
        )
        return wait_time

    # TODO - what happens if the scheduler fails? Does it try again or just wait until
    # the next time?
    async def start_task(self) -> None:
        while True:
            await asyncio.sleep(self._get_wait_interval())
            experiment = Experiment()
            log.info("Getting experiments from scheduler via background runner")
            await experiment.get_experiments_from_scheduler()
            await experiment.store_experiments()

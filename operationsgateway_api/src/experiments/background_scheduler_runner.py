import asyncio
from copy import copy
from datetime import datetime
import logging

from cron_converter import Cron
from dateutil import tz

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import ExperimentDetailsError
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

    def get_next_run_task_date(self):
        """
        TODO
        """
        runner_dates_copy = copy(self.runner_dates)
        return runner_dates_copy.next()

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

        wait_time = (scheduled_run - current_date).total_seconds()
        log.debug(
            "Number of seconds between now and next task run (%s): %d",
            self.task_name,
            wait_time,
        )
        return wait_time

    async def start_task(self) -> None:
        while True:
            await asyncio.sleep(self._get_wait_interval())
            log.info("Getting experiments from scheduler via background runner")
            try:
                experiment = Experiment()
                await experiment.get_experiments_from_scheduler()
                await experiment.store_experiments()
            except ExperimentDetailsError:
                log.warning(
                    "Background task to contact Scheduler failed. Retrying in %s "
                    "minutes",
                    Config.config.experiments.scheduler_background_retry_mins,
                )
                await asyncio.sleep(
                    Config.config.experiments.scheduler_background_retry_mins * 60,
                )
                try:
                    log.info("Retrying background task to contact Scheduler")
                    experiment = Experiment()
                    await experiment.get_experiments_from_scheduler()
                    await experiment.store_experiments()
                except ExperimentDetailsError:
                    # TODO - an admin should be alerted if it fails a second time. The
                    # JIMP emails someone (or a list of emails) if it fails but an
                    # Icinga check (write a file to the filesystem upon
                    # success/failure) might be better. We should work out what else
                    # needs monitoring/admins alerting to and decide on the best way to
                    # do this. Ingestion, 500s are other suggestions where an admin
                    # needs to be alerted to
                    log.error(
                        "Background task to contact Scheduler failed again. Task will "
                        "next be run at %s",
                        self.get_next_run_task_date(),
                    )

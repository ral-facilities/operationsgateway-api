import asyncio
import logging


from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import ExperimentDetailsError
from operationsgateway_api.src.experiments.experiment import Experiment
from operationsgateway_api.src.runner_abc import RunnerABC

log = logging.getLogger()


class BackgroundSchedulerRunner(RunnerABC):
    """
    A class that allows the retrieval of experiments and storing them in MongoDB via a
    background task. The frequency of this task is defined by the config option
    `scheduler_background_frequency` but we expect this to be around once a week.
    """

    def __init__(self, task_name: str) -> None:
        super().__init__(
            task_name=task_name,
            cron_string=Config.config.experiments.scheduler_background_frequency,
            timezone_str=Config.config.experiments.scheduler_background_timezone,
        )

    async def run_task(self) -> None:
        """
        Runs the task which contacts the Scheduler for new experiment details and store
        them in the database.

        If there is a problem during the task itself (i.e. dealing with experiments),
        the process is retried (after a configured amount of time). If the task fails a
        second time, this will be logged out as an error.
        """
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

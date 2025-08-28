from operationsgateway_api.src.backup.x_root_d_copy_runner import XRootDCopyRunner
from operationsgateway_api.src.experiments.background_scheduler_runner import (
    BackgroundSchedulerRunner,
)

scheduler_runner = BackgroundSchedulerRunner("Experiments Contact to Scheduler")
x_root_d_copy_runner = XRootDCopyRunner()

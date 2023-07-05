from pathlib import Path
import socket
from subprocess import PIPE, Popen
import sys
import threading
from time import sleep

from util.realistic_data.ingest.config import Config


class APIStarter:
    def __init__(self) -> None:
        if Config.config.script_options.launch_api:
            self.api_alive = False
            self.process = Popen(
                [
                    "poetry",
                    "run",
                    "gunicorn",
                    "operationsgateway_api.src.main:app",
                    "--workers",
                    Config.config.api.gunicorn_num_workers,
                    "--worker-class",
                    "uvicorn.workers.UvicornWorker",
                    "-b",
                    f"{Config.config.api.host}:{Config.config.api.port}",
                    "--log-config",
                    str(Path(Config.config.api.log_config_path)),
                ],
                stdout=PIPE,
                stderr=PIPE,
            )
            print("API startup commencing via subprocess")
            self.check_if_alive()
        else:
            self.api_alive = True
            self.process = None

    def check_if_alive(self) -> None:
        print("Checking if API started")
        while not self.api_alive:
            self.api_alive = self.is_api_alive()
            sleep(1)
            print("API not started yet...")
            # Check for the return code to see if the API started successfully
            self.process.poll()
            if self.process.returncode is not None and self.process.returncode != 0:
                t = threading.Thread(
                    target=APIStarter.clear_buffers,
                    args=(self.process, True),
                )
                t.start()
                sys.exit("API has failed to start up, please see output above")

    def is_api_alive(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        try:
            s.connect((Config.config.api.host, int(Config.config.api.port)))
            return True
        except Exception:
            return False

    @staticmethod
    def clear_buffers(process: Popen, output=False) -> None:
        out = process.stdout.read()
        err = process.stderr.read()
        if output:
            print(out.decode("utf-8"))
            print(err.decode("utf-8"))

    def kill(self) -> None:
        self.process.kill()
        print(f"API stopped on {Config.config.api.host}:{Config.config.api.port}")

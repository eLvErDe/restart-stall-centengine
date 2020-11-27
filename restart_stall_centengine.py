#!/usr/bin/python3


"""
Restart centreon-engine if it looks like being dead
(but process is still running, that's why I had to find some logic)
"""


# pylint: disable=line-too-long,bad-continuation


import os
import sys
import logging
import argparse
import datetime
import subprocess
import smtplib
from email.message import EmailMessage
from typing import List

if os.getenv("NO_LOGS_TS", None) is not None:
    LOG_FORMATTER = "%(levelname)-8s [%(name)s] %(message)s"
else:
    LOG_FORMATTER = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"

logging.basicConfig(level=logging.INFO, format=LOG_FORMATTER, stream=sys.stdout)
LOGGER = logging.getLogger("CentreonEngineRestarter")

try:
    import psutil  # type: ignore
except ImportError:
    LOGGER.error("Python module psutil not found, please run yum/apt install python3-psutil")
    sys.exit(2)


def get_status_file_date(path: str = "/var/log/centreon-engine/status.dat") -> datetime.datetime:
    """ Get status.dat last update timestamp """

    update_ts = datetime.datetime.fromtimestamp(os.path.getmtime(path)).replace(microsecond=0)
    return update_ts


def get_engine_zombies_process(username: str = "centreon-engine") -> List[psutil.Process]:
    """ Get process related to centreon-engine and return list of zombies """

    zombies = []
    for process in psutil.process_iter():
        if process.username() == username and process.status() == "zombie":
            zombies.append(process)
    return zombies


def cli_args() -> argparse.Namespace:
    """ Get command line arguments """

    parser = argparse.ArgumentParser(description="Restart stall centreon-engine service", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--status-dat-path", type=str, default="/var/log/centreon-engine/status.dat", help="Path to centreon-engine status.dat file")
    parser.add_argument("--status-dat-max-min", type=int, default=5, help="Engine status.dat file must have been updated within the last N minutes")
    parser.add_argument("--engine-username", type=str, default="centreon-engine", help="Username running centengine service")
    parser.add_argument("--engine-restart-cmd", type=str, default="systemctl restart centengine", help="Command to run to restart centengine service")
    parser.add_argument("--email-addr", type=str, nargs="?", metavar="root", help="Send an email (using local SMTP server) when a restart occurs, optional")

    parsed = parser.parse_args()
    return parsed


def main() -> None:
    """ Check status.dat update timestamp, zombie process and decide to reload centreon-engine service if needed """

    config = cli_args()

    try:
        status_date_update_ts = get_status_file_date(config.status_dat_path)
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.error("Unable to check %s update timestamp: %s: %s", config.status_dat_path, exc.__class__.__name__, exc)
        sys.exit(3)

    try:
        zombies = get_engine_zombies_process(config.engine_username)
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.error("Unable to check for %s zombies processes: %s: %s", config.engine_username, exc.__class__.__name__, exc)
        sys.exit(4)

    now_ts = datetime.datetime.now()
    max_delta = datetime.timedelta(minutes=config.status_dat_max_min)

    has_outdated_status = False
    has_zombie_processes = False
    if now_ts - max_delta > status_date_update_ts:
        LOGGER.warning(
            "Engine %s file has not been updated in the last %d minutes, last modification at %s",
            config.status_dat_path,
            config.status_dat_max_min,
            status_date_update_ts,
        )
        has_outdated_status = True
    if zombies:
        LOGGER.warning("Found %d zombie processes for user %s", len(zombies), config.engine_username)
        has_zombie_processes = True

    if has_outdated_status and has_zombie_processes:
        LOGGER.error("Centreon engine is probably crashed, restarting it")
        try:
            _output = subprocess.check_output(config.engine_restart_cmd, stderr=subprocess.STDOUT, shell=True)
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error("Centreon engine could not be restarted: %s: %s", exc.__class__.__name__, exc)
        else:
            if config.email_addr:
                msg = EmailMessage()
                msg["Subject"] = "Stall centreon engine has been restarted"
                msg["From"] = config.email_addr
                msg["To"] = config.email_addr
                msg.set_content("Check syslog for more information")
                with smtplib.SMTP("localhost") as smtp_server:
                    smtp_server.send_message(msg)


if __name__ == "__main__":

    main()

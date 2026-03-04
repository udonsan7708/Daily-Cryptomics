"""Daily Cryptomics – Entry Point.

Usage:
    python main.py

Designed to be called by a cron job or OpenClaw scheduler.
Exit codes:
    0 – success (tweet published)
    1 – pipeline failure (check logs)
    2 – configuration error (missing env variable)
"""

from __future__ import annotations

import sys

from src.agents.daily_cryptomics import DailyCryptomicsAgent
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger("daily_cryptomics.main")


def main() -> int:
    try:
        config = Config.from_env()
    except EnvironmentError as exc:
        logger.critical("Configuration error: %s", exc)
        return 2

    agent = DailyCryptomicsAgent(config)
    report = agent.run()
    return 0 if report.success else 1


if __name__ == "__main__":
    sys.exit(main())

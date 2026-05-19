#!/usr/bin/env python3
"""Garmin Connect Weight Deletion Utility.

Allows users to delete weight records for specific dates from Garmin Connect.

Usage:
    # Delete weight records for specific dates
    PYTHONPATH=. uv run python scripts/delete_weights.py 2026-05-19 2026-05-20

    # Display this help message
    PYTHONPATH=. uv run python scripts/delete_weights.py --help
"""

import argparse
import logging
import sys

from healthbridge.client import GarminClient
from healthbridge.config import get_settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("delete_weights")


def main():
    parser = argparse.ArgumentParser(
        description="Delete weight records from Garmin Connect for specific dates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "dates",
        metavar="YYYY-MM-DD",
        nargs="+",
        help="Date(s) for which to delete weight entries (space-separated).",
    )
    args = parser.parse_args()

    # Verify settings has token
    settings = get_settings()
    if not settings.has_token:
        logger.error(
            "Garmin Connect token is not configured. "
            "Please run 'python scripts/get_garmin_token.py' to generate a token, "
            "and configure GARMIN_TOKEN in your environment or .env file."
        )
        sys.exit(1)

    logger.info("Initializing Garmin Connect client and logging in...")
    client = GarminClient(settings)
    try:
        client.login()
    except Exception as e:
        logger.critical(f"Failed to log in: {e}")
        sys.exit(1)

    logger.info(f"Starting deletion of weight records for {len(args.dates)} dates...")
    successful_deletions = 0

    for date_str in args.dates:
        # Validate format is YYYY-MM-DD
        parts = date_str.split("-")
        if (
            len(parts) != 3
            or len(parts[0]) != 4
            or len(parts[1]) != 2
            or len(parts[2]) != 2
        ):
            logger.warning(
                f"Skipping invalid date format: '{date_str}'. Expected YYYY-MM-DD."
            )
            continue

        try:
            logger.info(f"Requesting deletion of all weigh-ins on: {date_str}...")
            # delete_all=True removes all entries for that date
            res = client.client.delete_weigh_ins(date_str, delete_all=True)
            logger.info(f"Completed for {date_str}. Result code: {res}")
            successful_deletions += 1
        except Exception as e:
            logger.error(f"Failed to delete records for {date_str}: {e}")

    logger.info(
        f"Finished! Successfully processed deletion requests for "
        f"{successful_deletions} dates."
    )


if __name__ == "__main__":
    main()

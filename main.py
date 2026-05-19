import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from healthbridge import GarminClient, WeightPayload, get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("healthbridge.main")


def run_original_demo(settings):
    """Executes the original stats-fetching and activity demonstration."""
    print("\n--- Fetching Daily Stats for Demo ---")
    client = GarminClient(settings)
    try:
        client.login()
        print("[+] Authentication Successful!")

        today = date.today().isoformat()
        print(f"\n--- Fetching Daily Stats for {today} ---")
        try:
            stats = client.get_stats(today)
            steps = stats.get("totalSteps", 0)
            goal = stats.get("stepsGoal", 0)
            cal_active = stats.get("activeCalories", 0)
            cal_base = stats.get("bmrCalories", 0)

            print(
                f"Steps:           {steps:,} / {goal:,} "
                + ("🎉" if steps >= goal else "")
            )
            print(f"Active Calories: {cal_active} kcal")
            print(f"Base Calories:   {cal_base} kcal")
            print(f"Total Calories:  {cal_active + cal_base} kcal")
        except Exception as e:
            logger.warning(
                f"Could not fetch today's stats (perhaps no data synced yet?): {e}"
            )

        print("\n--- Fetching Recent Activities ---")
        try:
            activities = client.get_activities(limit=3)
            if not activities:
                print("No recent activities found.")
            for i, act in enumerate(activities, 1):
                name = act.get("activityName", "Unknown Activity")
                type_name = act.get("activityType", {}).get("typeKey", "unknown")
                start_time = act.get("startTimeLocal", "unknown time")
                dist_m = act.get("distance", 0)
                dist_km = dist_m / 1000.0 if dist_m else 0.0
                duration_sec = act.get("duration", 0)
                dur_min = duration_sec / 60.0 if duration_sec else 0.0

                print(
                    f"{i}. {name} ({type_name})"
                    f"\n   Start Time: {start_time}"
                    f"\n   Distance:   {dist_km:.2f} km"
                    f"\n   Duration:   {dur_min:.1f} mins"
                )
        except Exception as e:
            logger.warning(f"Could not fetch activities: {e}")

    except Exception as e:
        logger.critical(f"\n[-] Authentication failed: {e}")
        print("Please check your email and password inside the '.env' file.")
        sys.exit(1)


def main():
    """Main entry point for the HealthBridge demo and weight sync application."""
    print("=" * 60)
    print("              HealthBridge Garmin Connect CLI             ")
    print("=" * 60)

    # Setup Argparse
    parser = argparse.ArgumentParser(
        description=(
            "Sync weight data to Garmin Connect with delta detection "
            "and deduplication."
        )
    )
    parser.add_argument(
        "--payload-json",
        type=str,
        help=(
            "Raw JSON payload string to parse and sync "
            '(e.g. \'{"poids": "...", "date": "..."}\')'
        ),
    )
    parser.add_argument(
        "--payload-file",
        type=str,
        help="Path to a JSON file containing the payload to parse and sync.",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=3,
        help="Number of past months to check for duplicates (default: 3)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help=(
            "Maximum number of existing records to retrieve for duplicate "
            "check (default: 100)"
        ),
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help=(
            "Run the original Garmin Connect stats demo instead of "
            "syncing weight payload."
        ),
    )

    args = parser.parse_args()

    # 1. Load Settings
    try:
        settings = get_settings()
    except ValidationError as e:
        logger.error("Configuration validation failed:")
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err["loc"])
            logger.error(f"  {loc}: {err['msg']} (input: {err.get('input')})")
        sys.exit(1)

    # 2. Check if token exists
    if not settings.has_token:
        print("\n[!] Garmin Connect token is not configured!")
        print("Please perform the following steps:")
        print(" 1. Run the token retriever script to log in and get your token:")
        print("    PYTHONPATH=. uv run python scripts/get_garmin_token.py")
        print(" 2. Save the token as GARMIN_TOKEN in your '.env' file or environment")
        print(" 3. Re-run this application\n")
        sys.exit(0)

    # 3. Parse inputs to find weight payload
    payload_data = None

    if args.payload_json:
        try:
            payload_data = json.loads(args.payload_json)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON string passed to --payload-json: {e}")
            sys.exit(1)

    elif args.payload_file:
        file_path = Path(args.payload_file)
        if not file_path.exists():
            logger.error(f"Payload file not found: {file_path}")
            sys.exit(1)
        try:
            with open(file_path, encoding="utf-8") as f:
                payload_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read/parse payload file {file_path}: {e}")
            sys.exit(1)

    elif os.environ.get("PAYLOAD_JSON"):
        env_val = os.environ["PAYLOAD_JSON"]
        try:
            payload_data = json.loads(env_val)
        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid JSON string in PAYLOAD_JSON environment variable: {e}"
            )
            sys.exit(1)

    # 4. Route based on arguments
    if payload_data is None or args.demo:
        if not args.demo:
            logger.info(
                "No weight payload provided via CLI arguments or environment variables."
            )
            logger.info("Falling back to demo mode. Use --help to view options.")
        run_original_demo(settings)
    else:
        # Sync weight payload
        logger.info("Weight payload detected. Starting parse and sync...")
        try:
            payload = WeightPayload(**payload_data)
            logger.info(
                f"Parsed {len(payload.entries)} weight entries "
                "(after date-based deduplication)."
            )
        except ValidationError as e:
            logger.error("Payload validation failed:")
            for err in e.errors():
                loc = " -> ".join(str(x) for x in err["loc"])
                logger.error(f"  {loc}: {err['msg']}")
            sys.exit(1)

        client = GarminClient(settings)
        try:
            client.login()
            logger.info("Authentication Successful!")

            uploaded = client.sync_weights(
                payload, months=args.months, limit=args.limit
            )
            print(
                f"\n[+] Sync Completed! Uploaded {uploaded} "
                "new records to Garmin Connect.\n"
            )
        except Exception as e:
            logger.critical(f"\n[-] Sync failed: {e}")
            sys.exit(1)

    print("=" * 60)
    print("Execution completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

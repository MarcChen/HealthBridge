import logging
import sys

from pydantic import ValidationError

from healthbridge import GarminClient, get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("healthbridge.upload_weights")


# Raw payload similar to the error logs in temp.md
PAYLOAD = {
    "poids": """74.5
74
72.69999694824219
72.19999694824219
72.69999694824219
71.09999847412109
71.80000305175781
73.80000305175781
73.09999847412109
73.09999847412109
72.19999694824219
71.5
71.5
72.5
71.80000305175781
71.80000305175781
71.80000305175781
72.80000305175781
72.19999694824219
72.19999694824219
71.69999694824219
71.69999694824219
71.59999847412109
68.69999694824219
68.69999694824219
67.19999694824219
67.19999694824219
76.90000152587891
76.90000152587891
75.90000152587891""",
    "date": """2025-12-06
2025-12-13
2025-12-17
2025-12-17
2025-12-18
2025-12-22
2025-12-24
2025-12-24
2025-12-25
2025-12-25
2025-12-25
2025-12-25
2025-12-26
2025-12-26
2025-12-26
2025-12-27
2025-12-27
2025-12-28
2025-12-28
2025-12-29
2025-12-29
2025-12-29
2025-12-30
2026-01-02
2026-01-02
2026-01-05
2026-01-05
2026-01-07
2026-01-07
2026-01-10""",
}


def parse_payload(payload: dict) -> list[tuple[str, float]]:
    """Parse raw weight and date newline-separated lists into a structured format."""
    weights = [
        float(w.strip()) for w in payload["poids"].strip().split("\n") if w.strip()
    ]
    dates = [d.strip() for d in payload["date"].strip().split("\n") if d.strip()]

    if len(weights) != len(dates):
        raise ValueError(
            f"Payload mismatch: Found {len(weights)} weights and {len(dates)} dates."
        )

    return list(zip(dates, weights, strict=True))


def main():
    print("=" * 60)
    print("        Garmin Connect Weight Upload Demonstration         ")
    print("=" * 60)

    # 1. Parse data
    try:
        entries = parse_payload(PAYLOAD)
        print(f"[+] Successfully parsed {len(entries)} weight records.")
    except Exception as e:
        logger.error(f"Failed to parse payload: {e}")
        sys.exit(1)

    # 2. Load Settings
    try:
        settings = get_settings()
    except ValidationError as e:
        logger.error("Configuration validation failed:")
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err["loc"])
            logger.error(f"  {loc}: {err['msg']}")
        sys.exit(1)

    if not settings.has_credentials:
        print("\n[!] Garmin Connect credentials are not configured!")
        print("Please set up '.env' with your GARMIN_EMAIL and GARMIN_PASSWORD first.")
        sys.exit(0)

    # 3. Connect to Garmin
    print(f"Connecting to Garmin Connect as: {settings.garmin_email}")
    client = GarminClient(settings)

    try:
        client.login()
        print("[+] Authentication Successful!")

        # 4. Upload each entry
        print(f"\nUploading {len(entries)} entries to Garmin Connect...")
        for i, (date_str, weight) in enumerate(entries, 1):
            # Using 'add_body_composition' to log the weight measurement.
            # You can also supply details like fat percentage, bone mass, etc.
            # We set a placeholder morning timestamp e.g. T08:00:00
            iso_timestamp = f"{date_str}T08:00:00"
            print(f"[{i}/{len(entries)}] Uploading: {weight:.2f} kg on {date_str}...")

            try:
                # Call the underlying Garmin API client
                client.client.add_body_composition(
                    timestamp=iso_timestamp,
                    weight=weight,
                )
                logger.info(f"Successfully uploaded {weight} kg for {date_str}.")
            except Exception as upload_err:
                logger.error(
                    f"Failed to upload {weight} kg for {date_str}: {upload_err}"
                )

    except Exception as e:
        logger.critical(f"\n[-] Authentication failed: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Weight upload completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

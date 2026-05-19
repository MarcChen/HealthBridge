import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from garminconnect import Garmin

from healthbridge.config import Settings, get_settings
from healthbridge.models import WeightPayload

logger = logging.getLogger(__name__)


class GarminClient:
    """A high-level client wrapper around the Garmin Connect API."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client: Garmin | None = None

    @property
    def client(self) -> Garmin:
        """Access the underlying Garmin Connect client.

        Initializes and logs in if not already done.
        """
        if not self._client:
            self.login()
        assert self._client is not None
        return self._client

    def login(self) -> None:
        """Authenticate with Garmin Connect.

        Loads the session token from configuration. Fallback to credentials if provided.
        """
        if not self.settings.has_auth:
            raise ValueError(
                "Neither Garmin Connect token nor credentials are configured. "
                "Please configure GARMIN_TOKEN or credentials "
                "(GARMIN_EMAIL/GARMIN_PASSWORD) in your environment or .env file."
            )

        token_path_str = str(self.settings.garmin_token_path)
        if not token_path_str.endswith(".json"):
            token_path = Path(self.settings.garmin_token_path) / "garmin_tokens.json"
        else:
            token_path = Path(self.settings.garmin_token_path)
        token_path = token_path.resolve()
        token_path.parent.mkdir(parents=True, exist_ok=True)

        if self.settings.has_token:
            token_raw = self.settings.garmin_token.get_secret_value()
            try:
                import json

                token_dict = json.loads(token_raw)
                logger.info(f"Loaded token format keys: {list(token_dict.keys())}")
            except Exception as e:
                logger.error(f"Loaded token is not a valid JSON structure: {e}")

            token_path.write_text(
                token_raw,
                encoding="utf-8",
            )

        # Initialize the underlying client with settings credentials
        self._client = Garmin(
            email=self.settings.email_or_username,
            password=self.settings.password_str,
            is_cn=self.settings.garmin_is_cn,
        )

        try:
            logger.info("Logging in...")
            # We call login passing the tokenstore path as a positional argument.
            # garminconnect will handle loading from this path. If it fails/expires
            # it will log in using credentials and save new tokens to token_path.
            self._client.login(str(token_path))
            logger.info("Garmin Connect login successful.")
        except Exception as e:
            logger.error(f"Failed to log in to Garmin Connect: {e}")
            self._client = None
            raise e

    def get_stats(self, date_str: str) -> dict[str, Any]:
        """Fetch general stats for a specific date (Format: YYYY-MM-DD)."""
        logger.info(f"Fetching health stats for {date_str}...")
        return self.client.get_stats(date_str)

    def get_body_composition(self, start_date: str, end_date: str) -> dict[str, Any]:
        """Fetch body composition (weight, body fat, etc.) between dates."""
        logger.info(f"Fetching body composition from {start_date} to {end_date}...")
        # Under the hood, this calls the body composition endpoint
        return self.client.get_body_composition(start_date, end_date)

    def get_sleep_data(self, date_str: str) -> dict[str, Any]:
        """Fetch sleep statistics for a specific date (Format: YYYY-MM-DD)."""
        logger.info(f"Fetching sleep data for {date_str}...")
        return self.client.get_sleep_data(date_str)

    def get_activities(self, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch the most recent physical activities."""
        logger.info(f"Fetching last {limit} activities...")
        return self.client.get_activities(0, limit)

    def get_weights(
        self, months: int = 1, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve weight records from Garmin Connect for the past X months.

        Optionally limits the number of returned entries to the last Y points.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)

        logger.info(
            "Retrieving weight records from %s to %s...",
            start_date.isoformat(),
            end_date.isoformat(),
        )
        try:
            data = self.get_body_composition(
                start_date.isoformat(), end_date.isoformat()
            )
        except Exception as e:
            logger.error(f"Failed to fetch body composition: {e}")
            return []

        weigh_ins = data.get("dateWeightList", [])

        cleaned_weigh_ins = []
        for entry in weigh_ins:
            weight_raw = entry.get("weight")
            if weight_raw is None:
                continue

            # Normalize weight: if raw > 1000 (in grams), convert to kg
            weight_kg = weight_raw / 1000.0 if weight_raw > 1000.0 else weight_raw
            # Garmin API returns calendarDate as YYYY-MM-DD,
            # while date is a timestamp
            date_str = entry.get("calendarDate") or entry.get("date")
            if isinstance(date_str, int):
                from datetime import datetime

                date_str = datetime.utcfromtimestamp(date_str / 1000.0).strftime(
                    "%Y-%m-%d"
                )

            if not date_str:
                continue

            cleaned_weigh_ins.append(
                {
                    "date": date_str,
                    "weight": weight_kg,
                    "timestamp": entry.get("timestamp"),
                }
            )

        # Sort by date/timestamp descending to get the most recent ones first
        cleaned_weigh_ins.sort(
            key=lambda x: x.get("timestamp") or x.get("date") or "",
            reverse=True,
        )

        if limit is not None:
            cleaned_weigh_ins = cleaned_weigh_ins[:limit]

        # Return in chronological order
        cleaned_weigh_ins.reverse()
        return cleaned_weigh_ins

    def sync_weights(
        self, payload: WeightPayload, months: int = 1, limit: int | None = None
    ) -> int:
        """Delta-sync new weight entries to Garmin Connect.

        Fetches existing weights for past months/limit, compares dates,
        and only uploads the entries from payload that do not exist yet.
        """
        logger.info("Starting weight delta-sync...")
        existing_weigh_ins = self.get_weights(months=months, limit=limit)
        existing_dates = {w["date"] for w in existing_weigh_ins if w.get("date")}

        logger.info(
            f"Found {len(existing_dates)} existing weigh-in dates in Garmin Connect."
        )

        uploaded_count = 0
        for entry in payload.entries:
            date_str = entry.date.isoformat()
            if date_str in existing_dates:
                logger.info(f"Weight entry for {date_str} already exists. Skipping.")
                continue

            # Upload new weight record
            timestamp = f"{date_str}T08:00:00"
            logger.info(
                f"Uploading new weight entry: {entry.weight} kg for {date_str}..."
            )

            try:
                self.client.add_body_composition(
                    timestamp=timestamp,
                    weight=entry.weight,
                )
                logger.info(f"Successfully uploaded {entry.weight} kg for {date_str}.")
                uploaded_count += 1
            except Exception as e:
                logger.error(f"Failed to upload weight for {date_str}: {e}")
                raise e

        logger.info(f"Weight sync completed. Uploaded {uploaded_count} new entries.")
        return uploaded_count

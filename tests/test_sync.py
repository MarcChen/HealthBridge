import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from healthbridge.client import GarminClient
from healthbridge.config import Settings
from healthbridge.models import WeightPayload


class TestWeightPayload(unittest.TestCase):
    """Unit tests for the WeightPayload Pydantic model parsing and validation."""

    def test_parsing_success(self):
        # Sample payload similar to the user's logs
        payload_data = {
            "poids": "74.5\n74.0\n72.7",
            "date": "2025-12-06\n2025-12-13\n2025-12-17",
        }
        payload = WeightPayload(**payload_data)

        self.assertEqual(len(payload.entries), 3)
        self.assertEqual(payload.entries[0].date, date(2025, 12, 6))
        self.assertEqual(payload.entries[0].weight, 74.5)
        self.assertEqual(payload.entries[1].date, date(2025, 12, 13))
        self.assertEqual(payload.entries[1].weight, 74.0)
        self.assertEqual(payload.entries[2].date, date(2025, 12, 17))
        self.assertEqual(payload.entries[2].weight, 72.7)

    def test_length_mismatch_raises_error(self):
        # 3 weights, 2 dates
        payload_data = {
            "poids": "74.5\n74.0\n72.7",
            "date": "2025-12-06\n2025-12-13",
        }
        with self.assertRaises(ValidationError):
            WeightPayload(**payload_data)

    def test_date_based_deduplication(self):
        # Multiple weigh-ins on 2025-12-17. The last weight '72.2' should win.
        payload_data = {
            "poids": "74.5\n74.0\n72.7\n72.2",
            "date": "2025-12-06\n2025-12-13\n2025-12-17\n2025-12-17",
        }
        payload = WeightPayload(**payload_data)

        # Should be deduplicated to 3 entries
        self.assertEqual(len(payload.entries), 3)

        # 2025-12-17 should have the last value: 72.2
        entry_17 = next(e for e in payload.entries if e.date == date(2025, 12, 17))
        self.assertEqual(entry_17.weight, 72.2)

        # List should remain chronologically sorted
        self.assertEqual(payload.entries[0].date, date(2025, 12, 6))
        self.assertEqual(payload.entries[1].date, date(2025, 12, 13))
        self.assertEqual(payload.entries[2].date, date(2025, 12, 17))


class TestGarminClientSync(unittest.TestCase):
    """Unit tests for the GarminClient get_weights and sync_weights logic."""

    def setUp(self):
        self.settings = Settings(
            garmin_email="test@example.com",
            garmin_password="secure_password",
        )
        self.client = GarminClient(settings=self.settings)

    @patch("healthbridge.client.GarminClient.get_body_composition")
    def test_get_weights_clean_and_normalize(self, mock_get_body_composition):
        # Garmin API returns weight in grams (e.g. 74500.0) or kilograms.
        # Let's test a mix of both to verify defensive parsing.
        mock_get_body_composition.return_value = {
            "dateWeightList": [
                {
                    "date": "2025-12-06",
                    "weight": 74500.0,
                    "timestamp": "2025-12-06T08:00:00",
                },
                {
                    "date": "2025-12-13",
                    "weight": 74.0,  # Already in kg
                    "timestamp": "2025-12-13T09:30:00",
                },
            ]
        }

        weights = self.client.get_weights(months=1)

        self.assertEqual(len(weights), 2)
        # Verify 74500.0 grams was correctly normalized to 74.5 kg
        self.assertEqual(weights[0]["weight"], 74.5)
        self.assertEqual(weights[0]["date"], "2025-12-06")

        # Verify 74.0 was kept as 74.0 kg
        self.assertEqual(weights[1]["weight"], 74.0)
        self.assertEqual(weights[1]["date"], "2025-12-13")

    @patch("healthbridge.client.GarminClient.get_weights")
    @patch("healthbridge.client.GarminClient.client")
    def test_sync_weights_delta(self, mock_client_prop, mock_get_weights):
        # Setup existing weigh-in dates in Garmin
        mock_get_weights.return_value = [
            {"date": "2025-12-06", "weight": 74.5},
            {"date": "2025-12-13", "weight": 74.0},
        ]

        # Setup mock Garmin client
        mock_garmin = MagicMock()
        mock_client_prop.add_body_composition = mock_garmin.add_body_composition
        self.client._client = mock_garmin

        # Incoming payload contains 3 entries (2 existing dates, 1 new date)
        payload_data = {
            "poids": "74.5\n74.0\n72.7",
            "date": "2025-12-06\n2025-12-13\n2025-12-17",
        }
        payload = WeightPayload(**payload_data)

        # Run sync
        uploaded = self.client.sync_weights(payload, months=1)

        # Only 2025-12-17 should be uploaded (1 new record)
        self.assertEqual(uploaded, 1)

        # Verify Garmin add_body_composition was called exactly once with the new data
        mock_garmin.add_body_composition.assert_called_once_with(
            timestamp="2025-12-17T08:00:00",
            weight=72.7,
        )


if __name__ == "__main__":
    unittest.main()

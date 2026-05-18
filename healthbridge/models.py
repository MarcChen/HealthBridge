from datetime import date

from pydantic import BaseModel, Field, model_validator


class WeightEntry(BaseModel):
    """Represents a single parsed weight entry."""

    date: date
    weight: float


class WeightPayload(BaseModel):
    """Pydantic model representing the raw weight upload payload.

    Parses newline-separated strings of weights and dates, deduplicates entries
    by date (keeping the latest), and provides a sorted list of WeightEntry objects.
    """

    poids: str
    date: str
    entries: list[WeightEntry] = Field(default_factory=list, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def parse_and_validate(cls, data: dict) -> dict:
        """Parses and validates the raw fields into a sorted list of WeightEntry."""
        poids_raw = data.get("poids")
        date_raw = data.get("date")

        if poids_raw is None or date_raw is None:
            raise ValueError("Both 'poids' and 'date' fields are required.")

        # Handle string stripping and conversion to list
        if not isinstance(poids_raw, str) or not isinstance(date_raw, str):
            raise ValueError("Both 'poids' and 'date' must be strings.")

        weights_str = poids_raw.strip().split("\n")
        dates_str = date_raw.strip().split("\n")

        weights = [float(w.strip()) for w in weights_str if w.strip()]
        dates = [date.fromisoformat(d.strip()) for d in dates_str if d.strip()]

        if len(weights) != len(dates):
            raise ValueError(
                f"Payload mismatch: Found {len(weights)} weights and "
                f"{len(dates)} dates."
            )

        # Deduplicate by date: keep the last weigh-in for any given date
        entries_dict = {}
        for d, w in zip(dates, weights, strict=True):
            entries_dict[d] = WeightEntry(date=d, weight=w)

        # Sort chronologically by date
        sorted_entries = [entries_dict[d] for d in sorted(entries_dict.keys())]

        data["entries"] = sorted_entries
        return data

"""Read and validate the four PriVis datasets without writing to them."""

import argparse
import csv
from dataclasses import dataclass
from datetime import date
from io import StringIO
import logging
from pathlib import Path
import re

import pandas as pd


DEFAULT_DATA_FOLDER = Path(__file__).resolve().parent / "data" / "sample"
MAX_FILE_BYTES = 10 * 1024 * 1024
LOGGER = logging.getLogger(__name__)

SCHEMAS = {
    "users.csv": (
        "user_id", "name", "sam_account_name", "department",
        "role", "worker_type", "enabled", "end_date",
    ),
    "groups.csv": (
        "group_id", "group_name", "risk_level", "resource_scope", "description",
    ),
    "memberships.csv": (
        "user_id", "group_id", "approval_status", "approval_ticket", "approval_expires",
    ),
    "access_policy.csv": ("role", "group_id", "access_decision", "policy_reason"),
}
OPTIONAL_FIELDS = {"end_date", "approval_ticket", "approval_expires"}
CHOICES = {
    "enabled": {"TRUE", "FALSE"},
    "risk_level": {"Low", "Medium", "High", "Critical"},
    "approval_status": {"Not Required", "Missing", "Approved"},
    "access_decision": {"Allowed", "Denied", "Approval Required"},
}
DATE_FIELDS = {"end_date", "approval_expires"}


class DataValidationError(ValueError):
    """A missing, unreadable, or invalid dataset."""


@dataclass(frozen=True)
class Dataset:
    users: pd.DataFrame
    groups: pd.DataFrame
    memberships: pd.DataFrame
    access_policy: pd.DataFrame


def _read_csv(path, fields):
    if not path.is_file():
        raise DataValidationError(f"{path}: expected a CSV file.")
    try:
        with path.open("rb") as source:
            contents = source.read(MAX_FILE_BYTES + 1)
        if len(contents) > MAX_FILE_BYTES:
            raise DataValidationError(f"{path.name}: exceeds the 10 MiB file limit.")
        decoded = contents.decode("utf-8-sig")
    except (OSError, UnicodeError) as error:
        raise DataValidationError(f"{path}: could not read UTF-8 CSV ({error}).") from error

    reader = csv.reader(StringIO(decoded, newline=""), strict=True)
    records = []
    try:
        header = next(reader, [])
        if len(header) != len(fields) or set(header) != set(fields):
            expected = ", ".join(fields)
            raise DataValidationError(f"{path.name}: expected these columns: {expected}.")
        while True:
            line = reader.line_num + 1
            values = next(reader, None)
            if values is None:
                break
            if not values:
                continue
            location = f"{path.name}:{line}"
            if len(values) != len(header):
                raise DataValidationError(f"{location}: expected {len(header)} fields.")
            record = {
                field: _parse_value(field, value, location)
                for field, value in zip(header, values)
            }
            records.append((location, record))
    except csv.Error as error:
        raise DataValidationError(
            f"{path.name}:{reader.line_num}: invalid CSV ({error})."
        ) from error
    return records


def _parse_value(field, value, location):
    value = value.strip()
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise DataValidationError(f"{location}: {field} contains a control character.")
    if not value and field not in OPTIONAL_FIELDS:
        raise DataValidationError(f"{location}: {field} is required.")
    if field in CHOICES and value not in CHOICES[field]:
        choices = ", ".join(sorted(CHOICES[field]))
        raise DataValidationError(f"{location}: {field} must be one of {choices}.")
    if field == "enabled":
        return value == "TRUE"
    if field in DATE_FIELDS:
        if not value:
            return None
        try:
            if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                return date.fromisoformat(value)
        except ValueError:
            pass
        raise DataValidationError(f"{location}: {field} must be a valid YYYY-MM-DD date.")
    return value


def _unique_keys(records, *fields):
    keys = set()
    for location, record in records:
        key = tuple(record[field] for field in fields)
        if key in keys:
            names = ", ".join(fields)
            raise DataValidationError(f"{location}: duplicate key ({names}).")
        keys.add(key)
    return keys


def _check_reference(records, field, keys):
    for location, record in records:
        if (record[field],) not in keys:
            raise DataValidationError(f"{location}: {field} references an unknown record.")


def load_dataset(folder: str | Path = DEFAULT_DATA_FOLDER) -> Dataset:
    """Return validated DataFrames with boolean enabled values and Python dates."""
    folder = Path(folder)
    records = {name: _read_csv(folder / name, fields) for name, fields in SCHEMAS.items()}
    users = records["users.csv"]
    groups = records["groups.csv"]
    memberships = records["memberships.csv"]
    policy = records["access_policy.csv"]

    user_ids = _unique_keys(users, "user_id")
    _unique_keys(
        [(location, {"sam_account_name": row["sam_account_name"].casefold()})
         for location, row in users],
        "sam_account_name",
    )
    group_ids = _unique_keys(groups, "group_id")
    _unique_keys(memberships, "user_id", "group_id")
    _unique_keys(policy, "role", "group_id")
    _check_reference(memberships, "user_id", user_ids)
    _check_reference(memberships, "group_id", group_ids)
    _check_reference(policy, "group_id", group_ids)

    tables = [
        pd.DataFrame.from_records([row for _, row in records[name]], columns=fields)
        for name, fields in SCHEMAS.items()
    ]
    tables[0]["enabled"] = tables[0]["enabled"].astype(bool)
    LOGGER.info("Validated %d users, %d groups, %d memberships, and %d policies.",
                *(len(table) for table in tables))
    return Dataset(*tables)


def main():
    parser = argparse.ArgumentParser(description="Validate PriVis CSV data.")
    parser.add_argument("folder", nargs="?", type=Path, default=DEFAULT_DATA_FOLDER)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        load_dataset(args.folder)
    except DataValidationError as error:
        LOGGER.error("%s", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

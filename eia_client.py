import json
import os
import urllib.parse
import urllib.request
from datetime import datetime


API_BASE = "https://api.eia.gov/v2/electricity/rto/region-data/data/"


def build_url(api_key, respondent="CISO", start=None, end=None):
    params = {
        "api_key": api_key,
        "frequency": "hourly",
        "data[0]": "value",
        "facets[respondent][]": respondent,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    }

    if start is not None:
        params["start"] = start

    if end is not None:
        params["end"] = end

    return API_BASE + "?" + urllib.parse.urlencode(params)


def fetch_raw_eia_data(api_key, respondent="CISO", start=None, end=None):
    url = build_url(api_key, respondent, start, end)

    with urllib.request.urlopen(url) as response:
        data = response.read().decode("utf-8")

    return json.loads(data)


def get_hour_from_period(period):
    # EIA period format usually looks like: 2026-06-27T00
    dt = datetime.fromisoformat(period)
    return dt.hour


def normalize_label(value):
    if value is None:
        return ""

    return str(value).strip().lower()


def get_data_category(row):
    """
    Convert EIA's type/type-name labels into the names used by this program.

    EIA may use either short codes, such as D or DF, or longer names,
    such as Demand or Demand Forecast. This function checks both.
    """

    type_code = normalize_label(row.get("type"))
    type_name = normalize_label(row.get("type-name"))

    possible_labels = {type_code, type_name}

    if "d" in possible_labels or "demand" in possible_labels:
        return "actual_load"

    if (
            "df" in possible_labels
            or "demand forecast" in possible_labels
            or "forecast demand" in possible_labels
            or "day-ahead demand forecast" in possible_labels
    ):
        return "forecast_load"

    if "ng" in possible_labels or "net generation" in possible_labels:
        return "actual_generation"

    if (
            "ti" in possible_labels
            or "interchange" in possible_labels
            or "total interchange" in possible_labels
    ):
        return "interchange"

    return None


def print_unique_eia_types(rows):
    """
    Debug helper. Prints the type/type-name combinations returned by EIA.
    This helps verify whether demand forecast is being returned.
    """

    seen = set()

    for row in rows:
        type_code = row.get("type")
        type_name = row.get("type-name")
        seen.add((type_code, type_name))

    print("\nUnique EIA data types returned:")

    for type_code, type_name in sorted(seen):
        print(f"type = {type_code}, type-name = {type_name}")


def fetch_eia_records(respondent="CISO", start=None, end=None):
    api_key = os.getenv("EIA_API_KEY")

    if api_key is None:
        raise ValueError("Missing EIA_API_KEY environment variable")

    raw_data = fetch_raw_eia_data(api_key, respondent, start, end)
    rows = raw_data["response"]["data"]

    # Temporary diagnostic: confirms what labels EIA actually returned.
    print_unique_eia_types(rows)

    records_by_period = {}

    for row in rows:
        period = row["period"]
        category = get_data_category(row)

        if category is None:
            continue

        if row.get("value") is None:
            continue

        value = float(row["value"])

        if period not in records_by_period:
            records_by_period[period] = {
                "period": period,
                "hour": get_hour_from_period(period),
            }

        records_by_period[period][category] = value

    records = []

    for period in sorted(records_by_period):
        record = records_by_period[period]

        # The estimator needs actual load.
        # Forecast load is preferred, but generation/interchange can be used as fallback.
        if "actual_load" in record:
            records.append(record)

    # The API often includes the end timestamp too, giving 25 records for a 24-hour range.
    records = records[:24]

    # Align forecast load with actual load in case timestamps are offset.
    records = align_forecast_load(records)

    return records


def print_sample_eia_data(respondent="CISO", start=None, end=None):
    api_key = os.getenv("EIA_API_KEY")

    if api_key is None:
        raise ValueError("Missing EIA_API_KEY environment variable")

    raw_data = fetch_raw_eia_data(api_key, respondent, start, end)
    rows = raw_data["response"]["data"]

    print("Number of rows returned:", len(rows))
    print_unique_eia_types(rows)

    print("\nFirst few rows:")

    for row in rows[:10]:
        print(json.dumps(row, indent=2))

def align_forecast_load(records):
    """
    Try shifting forecast_load by several hours and keep the shift
    that best matches actual_load.

    This helps if EIA forecast timestamps are offset from actual
    demand timestamps.
    """

    if len(records) == 0:
        return records

    if any(record.get("forecast_load") is None for record in records):
        return records

    best_shift = 0
    best_error = None

    n = len(records)

    for shift in range(n):
        total_error = 0.0

        for i in range(n):
            shifted_forecast = records[(i + shift) % n]["forecast_load"]
            actual_load = records[i]["actual_load"]

            total_error += abs(shifted_forecast - actual_load)

        if best_error is None or total_error < best_error:
            best_error = total_error
            best_shift = shift

    aligned_records = []

    for i in range(n):
        new_record = records[i].copy()
        new_record["forecast_load"] = records[(i + best_shift) % n]["forecast_load"]
        new_record["forecast_shift_hours"] = best_shift
        aligned_records.append(new_record)

    print(f"Best forecast alignment shift: {best_shift} hours")

    return aligned_records
from datetime import datetime, timedelta

# Import drift functions
from drift_estimator import analyze_clock_drift, total_clock_drift

# Controls whether the program will use live data or sample data
USE_API = True
RESPONDENT = "CISO"   # California Independent System Operator - agency accessed through the EIA API
DAYS_BACK = 2         # Use recent completed data because generation can lag

# Builds a 24-hour data range for the API in the correct format.
# Returns start (= midnight of the target day) and end (= midnight of the next day)
def get_recent_completed_eia_range(days_back=DAYS_BACK):
    target_day = datetime.utcnow().date() - timedelta(days=days_back)

    start = f"{target_day}T00"
    end = f"{target_day + timedelta(days=1)}T00"

    return start, end

# For testing without access to the API
def get_sample_records():
    return [
        {"hour": 0, "forecast_load": 9800, "actual_load": 10000, "actual_generation": 9900},
        {"hour": 1, "forecast_load": 10100, "actual_load": 10000, "actual_generation": 10050},
        {"hour": 2, "forecast_load": 9900, "actual_load": 10000, "actual_generation": 10000},
    ]

# Prints algorithm output, hour by hour.
def print_drift_direction(drift):
    if drift > 0:
        print("Clock is estimated to run fast.")
    elif drift < 0:
        print("Clock is estimated to run slow.")
    else:
        print("Clock is estimated to stay accurate.")


def print_hourly_analysis(records):
    print("\nHourly drift analysis:") # Prints hour-by-hour output from the algorithm
    analysis = analyze_clock_drift(records)

    for row in analysis:
        print(
            f"Hour {row['hour']}: "
            f"forecast = {row['forecast_load']} "
            f"load = {row['actual_load']} "
            f"gen = {row['actual_generation']} "
            f"interchange = {row['interchange']} "
            f"increment = {row['drift_increment']:.2f}s, "
            f"total = {row['total_drift']:.2f}s, "
            f"sync needed = {row['sync_needed']}"
        )

# Program executable. Chooses data source, loads records, runs the algorithm, prints hourly and total results.
def main():
    if USE_API:
        from eia_client import fetch_eia_records

        start, end = get_recent_completed_eia_range()

        print(f"Using EIA data for {RESPONDENT}")
        print(f"Date range: {start} to {end}")

        # Pulls hourly records from the API
        records = fetch_eia_records(
            respondent=RESPONDENT,
            start=start,
            end=end
        )
    else:
        # Use local test records
        print("Using sample test records.")
        records = get_sample_records()

    print(f"Records loaded: {len(records)}")

    # Do not run algorithm if not records located.
    if len(records) == 0:
        print("No usable records were loaded. Check the API response or date range.")
        return

    # Return total accumulated drift over the 24-hour period.
    drift = total_clock_drift(records)

    print(f"\nEstimated clock drift: {drift:.2f} seconds")
    print_drift_direction(drift)

    # Print each hour's behavior and drift.
    print_hourly_analysis(records)


if __name__ == "__main__":
    main()
# Standard electric grid frequency (in Hz) for the U.S.
# Electric clocks assume this frequency to derive their time.
NOMINAL_FREQ = 60.0

# Estimated governor droop factor. NERC specifies a 3-5% range.
# A 4% droop means at a 100% power imbalance, frequency will lower or
# raise by 4% if load is greater or less than generation
DROOP = 0.04

# Convert droop percentage to Hz
DROOP_HZ = NOMINAL_FREQ * DROOP

# Data from the government (EIA) available hourly,
# we want a return value in seconds.
SECONDS_PER_HOUR = 3600

# If the accumulated clock drift reaches 20 seconds,
# the program signals to resync the clocks
DRIFT_THRESHOLD_SECONDS = 20.0


""" Estimates grid frequency deviation for an hourly record.
    This version uses ramp mismatch as the main algorithm. It compares how 
    much load changed from the previous hour to how much supply changed 
    from the previous hour. If load rises faster than supply, 
    the estimated frequency deviation is negative. If supply 
    rises faster than load, the estimated frequency deviation is positive.
"""
def estimate_frequency_deviation(current_record, previous_record):
    # The first record has no previous hour to compare against.
    # Return 0.0 so the algorithm starts from a known baseline.
    if previous_record is None:
        return 0.0

    actual_load = current_record["actual_load"]

    if actual_load == 0:
        raise ValueError("actual_load cannot be zero")

    # Supply is estimated using generation and interchange.
    # Positive interchange usually means export,
    # negative interchange usually means import.
    current_supply = (
            current_record.get("actual_generation", 0.0)
            - current_record.get("interchange", 0.0)
    )

    previous_supply = (
            previous_record.get("actual_generation", 0.0)
            - previous_record.get("interchange", 0.0)
    )

    # Load ramp is how much actual load changed between hours.
    load_ramp = current_record["actual_load"] - previous_record["actual_load"]

    # Supply ramp is how much estimated supply changed between hours.
    supply_ramp = current_supply - previous_supply

    # Unresolved imbalance is the difference between supply change and load change.
    # Negative means load increased more than supply.
    # Positive means supply increased more than load.
    imbalance_mw = supply_ramp - load_ramp

    # Convert imbalance from MW into a fraction of current load.
    imbalance_fraction = imbalance_mw / actual_load

    # Convert imbalance fraction into a frequency deviation.
    return DROOP_HZ * imbalance_fraction


# Core algorithm.
# Calculates a frequency deviation and converts it into clock drift for that hour.
# That drift is then added to the running total for hourly drift, and a signal
# is sent when accumulated drift exceeds a threshold.
# Returns a list of hourly analysis records
def analyze_clock_drift(records, threshold=DRIFT_THRESHOLD_SECONDS):
    total_drift = 0.0
    results = []

    for i, record in enumerate(records):
        # Pull previous hourly record for ramp comparison.
        # The first hour has no previous record.
        previous_record = records[i - 1] if i > 0 else None

        # Estimate how far the grid frequency is from 60 Hz
        delta_f = estimate_frequency_deviation(record, previous_record)

        # Convert frequency deviation into time drift in seconds
        drift_increment = (delta_f / NOMINAL_FREQ) * SECONDS_PER_HOUR

        # Add this hour's time drift to the accumulated clock error.
        total_drift += drift_increment

        # A sync is needed once the clock is too slow or too fast.
        sync_needed = abs(total_drift) >= threshold

        results.append({
            "hour": record.get("hour"),
            "actual_load": record["actual_load"],
            "forecast_load": record.get("forecast_load"),
            "actual_generation": record.get("actual_generation"),
            "interchange": record.get("interchange"),
            "frequency_deviation": delta_f,
            "drift_increment": drift_increment,
            "total_drift": total_drift,
            "sync_needed": sync_needed,
        })

    return results


def total_clock_drift(records):
    # Helper method - Returns the final accumulated drift for the analyzed records.

    analysis = analyze_clock_drift(records)

    if len(analysis) == 0:
        return 0.0

    return analysis[-1]["total_drift"]
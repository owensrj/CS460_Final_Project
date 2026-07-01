import unittest

from drift_estimator import analyze_clock_drift, total_clock_drift, estimate_frequency_deviation


class TestDriftEstimator(unittest.TestCase):

    def test_first_hour_has_zero_frequency_deviation(self):
        current_record = {
            "hour": 0,
            "actual_load": 10000,
            "actual_generation": 10000,
            "interchange": 0,
            "forecast_load": 9900,
        }

        expected = 0.0
        actual = estimate_frequency_deviation(current_record, None)

        self.assertAlmostEqual(actual, expected, places=6)

    def test_frequency_deviation_when_load_rises_faster_than_supply(self):
        previous_record = {
            "hour": 0,
            "actual_load": 10000,
            "actual_generation": 10000,
            "interchange": 0,
        }

        current_record = {
            "hour": 1,
            "actual_load": 10100,
            "actual_generation": 10050,
            "interchange": 0,
        }

        # load ramp = 10100 - 10000 = 100
        # supply ramp = 10050 - 10000 = 50
        # imbalance = 50 - 100 = -50
        # frequency deviation = 2.4 * (-50 / 10100)
        expected = -0.0118811881
        actual = estimate_frequency_deviation(current_record, previous_record)

        self.assertAlmostEqual(actual, expected, places=6)

    def test_frequency_deviation_when_supply_rises_faster_than_load(self):
        previous_record = {
            "hour": 0,
            "actual_load": 10000,
            "actual_generation": 10000,
            "interchange": 0,
        }

        current_record = {
            "hour": 1,
            "actual_load": 10050,
            "actual_generation": 10150,
            "interchange": 0,
        }

        # load ramp = 10050 - 10000 = 50
        # supply ramp = 10150 - 10000 = 150
        # imbalance = 150 - 50 = 100
        # frequency deviation = 2.4 * (100 / 10050)
        expected = 0.0238805970
        actual = estimate_frequency_deviation(current_record, previous_record)

        self.assertAlmostEqual(actual, expected, places=6)

    def test_three_hour_total_clock_drift(self):
        records = [
            {
                "hour": 0,
                "actual_load": 10000,
                "actual_generation": 10000,
                "interchange": 0,
                "forecast_load": 9900,
            },
            {
                "hour": 1,
                "actual_load": 10100,
                "actual_generation": 10050,
                "interchange": 0,
                "forecast_load": 10000,
            },
            {
                "hour": 2,
                "actual_load": 10050,
                "actual_generation": 10150,
                "interchange": 0,
                "forecast_load": 9950,
            },
        ]

        # Hour 0 drift = 0.0 because there is no previous hour.
        #
        # Hour 1:
        # frequency deviation = -0.0118811881
        # drift = (-0.0118811881 / 60) * 3600 = -0.712871286
        #
        # Hour 2:
        # load ramp = 10050 - 10100 = -50
        # supply ramp = 10150 - 10050 = 100
        # imbalance = 100 - (-50) = 150
        # frequency deviation = 2.4 * (150 / 10050)
        # drift = 2.149253731
        #
        # total drift = 1.436382445
        expected = 1.436382445
        actual = total_clock_drift(records)

        self.assertAlmostEqual(actual, expected, places=6)

    def test_sync_signal_when_drift_reaches_threshold(self):
        records = [
            {
                "hour": 0,
                "actual_load": 10000,
                "actual_generation": 10000,
                "interchange": 0,
            },
            {
                "hour": 1,
                "actual_load": 12000,
                "actual_generation": 10000,
                "interchange": 0,
            },
        ]

        # Hour 0 drift = 0.0
        #
        # Hour 1:
        # load ramp = 12000 - 10000 = 2000
        # supply ramp = 10000 - 10000 = 0
        # imbalance = 0 - 2000 = -2000
        # frequency deviation = 2.4 * (-2000 / 12000) = -0.4
        # drift = (-0.4 / 60) * 3600 = -24 seconds
        #
        # With a 20 second threshold, sync should trigger at hour 1.
        analysis = analyze_clock_drift(records, threshold=20.0)

        self.assertFalse(analysis[0]["sync_needed"])
        self.assertTrue(analysis[1]["sync_needed"])
        self.assertAlmostEqual(analysis[1]["total_drift"], -24.0, places=6)


if __name__ == "__main__":
    unittest.main()
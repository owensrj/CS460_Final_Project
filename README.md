# CS460_Final_Project
## Grid Frequency Clock Drift Estimator

This Program estimates clock drift for synchronous electric clocks using hourly electric grid data accessed from the U.S. Energy Information Administration (EIA) via their API. 

Synchronous electric clocks determine time based on the standard electric grid frequency of 60 Hz. When grid frequency deviates above or below that value, clocks will run fast or slow. This project estimates that drift using hourly load, generation, power import/export (interchange), and demand forecast data. 

The implementation I decided on for the final submission uses a ramp-based approach. That means it compares how much electrical load changes hour over hour and compares that to how generation supply changes hour over hour. That load imbalance is then converted into a frequency deviation, and converted again to find how that affects clock drift over an accumulated 24-hour period. 

## Project Files
- 'main.py'
  Program access point. Loads data and prints the total and hourly clock drift results.
- 'drift_estimator.py'
  Core clock drift algorithm.
- 'eia_client.py'
  Connects to the EIA API and converts the API results to useable data fields
- 'test_drift_estimator.py'
  Unit tests for the drift estimation algorithm

## Requirements
Python standard library modules only.
Written using Python 3.

## EIA API KEY (IMPORTANT)
To use live EIA data, you will need a free EIA API KEY.
You can request the API key here:
https://www.eia.gov/opendata/register.php

After receiving your key, set it as an environment variable named:
```bash
EIA_API_KEY

if using macOS or Linux, you can set it temporarily in Terminal with:
export EIA_API_KEY="your_api_key_here"

I personally used IntelliJ and added the key through:
Run > Edit Configurations > Environment variables
and added my key at exactly the quoted section, no spaces:
EIA_API_KEY="your_api_key_here"

## Running the program
From the project folder run:
python main.py

## Running the tests
From the project folder run:
python -m unittest test_drift_estimator.py

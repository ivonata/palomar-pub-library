name: Re-seed ADS Library (Manual Trigger)

on:
  workflow_dispatch: # Enables the manual "Run workflow" button in Actions

jobs:
  seed-library:
    runs-on: ubuntu-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      - name: Execute ADS Seed Script
        env:
          ADS_DEV_KEY: ${{ secrets.ADS_DEV_KEY }}
        run: |
          python seed_library.py

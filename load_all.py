import pandas as pd
import load
from extract import extract_covid

load.build_state_relation()

# Counties + population for every state (one Census snapshot: April 2020)
failed = []
for state in load.STATE_FIPS:
    try:
        load.build_counties_relation(state, 4, 2020)
        print(f"{state} done")
    except Exception as e:
        failed.append(state)
        print(f"{state} FAILED: {e}")
print(f"Counties failed for: {failed or 'none'}")

for year in [2020, 2021, 2022, 2023]:
    print(f"Loading covid {year}...")
    if load.load_covid19_data(year) is None:
        continue

    # Re-read the same NYT file to name the counties load_covid19_data() skipped
    stored = {state_fips + county_fips for county_fips, state_fips in load.CURSOR.execute("SELECT county_fips, state_fips FROM counties")}
    url = f"https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties-{year}.csv"

    skipped = {}    # (state, county, fips) -> number of rows skipped
    for row in extract_covid(url):
        fips = row["fips"]
        if pd.isna(fips):
            key = (row["state"], row["county"], "no FIPS")
        elif fips in stored:
            continue
        else:
            key = (row["state"], row["county"], fips)
        skipped[key] = skipped.get(key, 0) + 1

    print(f"Skipped {len(skipped)} counties in {year}:")
    for (state, county, fips), rows in sorted(skipped.items()):
        print(f"  {state}, {county} ({fips}): {rows} rows")

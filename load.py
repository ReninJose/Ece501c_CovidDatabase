from extract import extract_population_data, extract_land_area, extract_covid
from database.connector import get_cursor, init
from datetime import datetime as dt
import sqlite3

init()  # Build using schemas defined in database/DDL.sql
CURSOR = get_cursor()   # Use this object to interact with the database

# State abbreviation -> FIPS code
STATE_FIPS = {
    "AL": 1,  "AK": 2,  "AZ": 4,  "AR": 5,  "CA": 6,  "CO": 8,  "CT": 9,
    "DE": 10, "DC": 11, "FL": 12, "GA": 13, "HI": 15, "ID": 16, "IL": 17,
    "IN": 18, "IA": 19, "KS": 20, "KY": 21, "LA": 22, "ME": 23, "MD": 24,
    "MA": 25, "MI": 26, "MN": 27, "MS": 28, "MO": 29, "MT": 30, "NE": 31,
    "NV": 32, "NH": 33, "NJ": 34, "NM": 35, "NY": 36, "NC": 37, "ND": 38,
    "OH": 39, "OK": 40, "OR": 41, "PA": 42, "RI": 44, "SC": 45, "SD": 46,
    "TN": 47, "TX": 48, "UT": 49, "VT": 50, "VA": 51, "WA": 53, "WV": 54,
    "WI": 55, "WY": 56, "PR": 72,
}


def insert_many(query, rows):
    # The savepoint lets a failed batch be undone without losing earlier
    # uncommitted inserts (e.g. counties rows before county_demographic)
    CURSOR.execute("SAVEPOINT insert_many")
    try:
        CURSOR.executemany(query, rows)
    except sqlite3.Error:
        CURSOR.execute("ROLLBACK TO insert_many")
        skipped = 0
        for row in rows:
            try:
                CURSOR.execute(query, row)
            except sqlite3.IntegrityError as row_error:
                if "UNIQUE constraint failed" not in str(row_error):
                    CURSOR.connection.rollback()
                    raise RuntimeError(f"Insert failed: {row_error}\n  Query: {query}\n  Row: {row}") from row_error
                skipped += 1
                print(f"Skipped duplicate ({row_error}): {row}")
            except sqlite3.Error as row_error:
                CURSOR.connection.rollback()
                raise RuntimeError(f"Insert failed: {row_error}\n  Query: {query}\n  Row: {row}") from row_error
        print(f"Skipped {skipped} duplicate row(s), inserted {len(rows) - skipped}")
    CURSOR.execute("RELEASE insert_many")


def build_state_relation():
    # Skip if every state in STATE_FIPS is already stored
    state_count = CURSOR.execute("SELECT COUNT(*) FROM states").fetchone()[0]
    if state_count >= len(STATE_FIPS):
        print("State data already exists")
        return None

    states = []
    for name, fips in STATE_FIPS.items():
        states.append({
            "state_fips": f"{fips:02d}",
            "state_name": name
        })

    # OR IGNORE: if the table is only partly filled, add just the missing states
    query = "INSERT OR IGNORE INTO states (state_fips, state_name) VALUES (:state_fips, :state_name)"
    insert_many(query, states)
    CURSOR.connection.commit()

    return True


def load_covid19_data(year):
    # This function loads in covid-19 data on county basis for the year 2020, 2021, 2022, and 2023
    # This data was gathered from nytimes database publicly available from Github
    if year not in [2020, 2021, 2022, 2023]:
        raise ValueError("year must be 2020, 2021, 2022, or 2023")

    url = f"https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties-{year}.csv"
    covid_data = extract_covid(url)

    processed_data = []
    for data in covid_data:
        try:
            state_fips, county_fips = data["fips"][:2], data["fips"][2:]
        except Exception as e:
            continue
        
        processed_data.append({
            "county_fips": county_fips,
            "state_fips": state_fips,
            "date": data["date"].strftime("%Y-%m-%d"), 
            "cases": data["infected_cases"],
            "deaths": data["deaths"]
        })

    query = "INSERT INTO covid (county_fips, state_fips, date, cases, deaths) VALUES (:county_fips, :state_fips, :date, :cases, :deaths)"
    insert_many(query, processed_data)
    CURSOR.connection.commit()

    return True
        

def build_counties_relation(state, month, year):
    state_id = STATE_FIPS.get(state.upper())
    if state_id is None:
        raise ValueError(f"Unknown state code: {state}")

    date = dt.strptime(f"{year}-{month}", "%Y-%m")    # Census data is monthly, so day defaults to 1

    # county_demographic stores state_fips as zero-padded text ("04") and date as "YYYY-MM-DD"
    state_fips = f"{state_id:02d}"
    date_str = date.strftime("%Y-%m-%d")

    population_exists = CURSOR.execute("SELECT * FROM county_demographic WHERE state_fips = ? AND date = ? LIMIT 1", (state_fips, date_str)).fetchone()
    if population_exists is not None:
        print(f"Population data for {state.upper()} {date_str} already exists")
        population_data = CURSOR.execute("SELECT * FROM county_demographic WHERE state_fips = ? AND date = ?", (state_fips, date_str)).fetchall()
        return None
    else:
        population_data = extract_population_data(state_id, month, year)
    
    area_data = extract_land_area(state_id)

    # County FIPS -> land area (km^2)
    area_by_fips = {a_data["county_fips"]: a_data["land_area"] for a_data in area_data}

    # Pre-calculation
    county_rows = []        # counties: static info, one row per county
    demographic_rows = []   # county_demographic: one row per county per date
    for pop_data in population_data:
        county_fips = pop_data["county_fips"]
        county_population = pop_data["population"]
        area = area_by_fips.get(county_fips)
        if area is None:
            raise Exception(f"Area data for county {pop_data['county_name']} ({county_fips}) from state {state} not found")
        population_density = round(county_population/area, 3)    #pop/km^2

        county_rows.append({
            "county_fips": county_fips,
            "state_fips": pop_data["state_fips"],
            "county_name": pop_data["county_name"],
            "area_sq_km": round(area, 3),
        })

        demographic_rows.append({
            "county_fips": county_fips,
            "state_fips": pop_data["state_fips"],
            "population": county_population,
            "population_density": population_density,
            "date": pop_data["date"].strftime("%Y-%m-%d"),
        })

    # A county may already be stored from an earlier month, so skip duplicates
    counties_query = \
        "INSERT OR IGNORE INTO counties (county_fips, state_fips, county_name, area_sq_km) \
            VALUES (:county_fips, :state_fips, :county_name, :area_sq_km)"

    demographic_query = \
        "INSERT INTO county_demographic (county_fips, state_fips, population, population_density, date) \
            VALUES (:county_fips, :state_fips, :population, :population_density, :date)"

    insert_many(counties_query, county_rows)
    insert_many(demographic_query, demographic_rows)
    CURSOR.connection.commit()

    return True     # Success




    
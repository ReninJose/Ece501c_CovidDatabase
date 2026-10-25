import requests
import pandas as pd
import os
import io
from datetime import datetime as dt
from dotenv import load_dotenv

load_dotenv(override=True)  # .env wins over a stale CENSUS_API_KEY already in the shell

POPULATION_URL = "https://api.census.gov/data/2023/pep/charv"
GEO_URL = "https://api.census.gov/data/2025/geoinfo"


def extract_population_data(state_fips, month, year):
    api_key = os.getenv("CENSUS_API_KEY")

    params = {
        "get": "NAME,POP",
        "for": "county:*",      # All counties
        "in": f"state:{state_fips:02d}",   
        "MONTH": month,
        "YEAR": year,
        "key": api_key,
    }
    try:
        response = requests.get(url=POPULATION_URL, params=params, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Census API request failed: {e}") from e

    # Census returns 204 with an empty body when no data matches the query
    if response.status_code == 204 or not response.text:
        raise ValueError(f"No data for state_fips={state_fips}, month={month}, year={year}")

    # In list form: [COUNTY_NAME, POP, MONTH, YEAR, STATE_FIPS, COUNTY_FIPS]
    population_data = []
    for p_data in response.json()[1:]:
        pop = {
            "county_fips": p_data[5],
            "state_fips": p_data[4],
            "county_name": p_data[0].split(",")[0],
            "population": int(p_data[1]),
            "date": dt.strptime(f"{p_data[3]}-{p_data[2]}", "%Y-%m")
        }

        population_data.append(pop)

    return population_data


def extract_land_area(state_fips):
    api_key = os.getenv("CENSUS_API_KEY")

    params = {
        "get": "NAME,AREALAND",
        "for": "county:*",      # All counties
        "in": f"state:{state_fips:02d}",   
        "key": api_key,
    }
    try:
        response = requests.get(url=GEO_URL, params=params, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Census API request failed: {e}") from e

    # Census returns 204 with an empty body when no data matches the query
    if response.status_code == 204 or not response.text:
        raise ValueError(f"No data for state_fips={state_fips}")
    
    # In list form: [COUNTY_NAME, LAND_AREA(SQUARE METERS), STATE_FIPS, COUNTY_FIPS]
    area_data = []
    for a_data in response.json()[1:]:
        area = {
            "county_fips": a_data[3],
            "state_fips": a_data[2],
            "county_name": a_data[0].split(",")[0],
            "land_area": float(a_data[1]) * 0.000001,  # Convert to Km^2,
        }   

        area_data.append(area)

    return area_data


def extract_covid(url):
    try:
        response = requests.get(url=url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
            raise RuntimeError(f"nytimes API request failed: {e}") from e
    
    # Census returns 204 with an empty body when no data matches the query
    if response.status_code == 204 or not response.text:
        raise ValueError(f"No data found for given url={url}")
    
    df = pd.read_csv(io.StringIO(response.text), dtype={"fips": "string"}, parse_dates=["date"])

    # In tuple form: (INDEX, DATE, COUNTY, STATE, FIPS, CASES, DEATHS)
    covid_data = []
    for col in df.itertuples():
        covid = {
            "date": col[1],
            "county": col[2],
            "state": col[3],
            "fips": col[4],
            "infected_cases": col[5],
            "deaths": col[6],
        }

        covid_data.append(covid)

    return covid_data

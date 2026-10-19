# Ece501c_CovidDatabase

A SQLite database of U.S. county-level COVID-19 cases and deaths, combined with county population and land area. Population and land area come from the U.S. Census Bureau API. COVID-19 data comes from the [New York Times COVID-19 dataset](https://github.com/nytimes/covid-19-data).

## Setup

Run the setup script from the project root:

```bash
source setup.sh
```

It does the following:
1. Creates a Python virtual environment in `.venv` and activates it.
2. Installs the packages in `requirements.txt`.
3. Asks for your Census API key and saves it to `.env`. You need a key to continue. Request one at https://api.census.gov/data/key_signup.html. Type `q` at the prompt to stop setup.
4. Deletes `database/covid.db` if it exists, so the database is rebuilt from `database/DDL.sql`. **This deletes any data you have already loaded.**

If you run `bash setup.sh` instead of `source setup.sh`, activate the environment afterwards with `source .venv/bin/activate`.

## Database tables

The schema is defined in `database/DDL.sql`. It is applied automatically when `load.py` is imported.

| Table | Contents | Primary key |
|---|---|---|
| `states` | State FIPS code and state abbreviation | `state_fips` |
| `counties` | County name and land area (km²) | `county_fips`, `state_fips` |
| `county_demographic` | County population and population density (people per km²) for a given month | `county_fips`, `state_fips`, `date` |
| `covid` | Daily cumulative COVID-19 cases and deaths per county | `county_fips`, `state_fips`, `date` |

FIPS codes are stored as zero-padded text: state `"04"` (Arizona) and county `"019"` (Pima County). Dates are stored as `YYYY-MM-DD` text.

## Loading data with `load.py`

Importing `load.py` creates any missing tables in `database/covid.db`. Then call the functions you need. Run them from the project root with the virtual environment active:

```bash
python -c "import load; load.build_state_relation()"
```

Or from an interactive Python session:

```python
import load

load.build_state_relation()                 # 1. Fill the states table
load.build_counties_relation("AZ", 4, 2020) # 2. Arizona counties, population as of April 2020
load.load_covid19_data(2020)                # 3. NYT COVID-19 data for every county in 2020
```

Run `build_state_relation()` first, because the other tables refer to states.

### `build_state_relation()`

Fills the `states` table with every state listed in `STATE_FIPS` in `load.py`. If the table is already full, it prints `State data already exists` and does nothing. If it is only partly filled, it adds the missing states.

### `build_counties_relation(state, month, year)`

Loads the counties of one state for one month.

| Argument | Type | Example | Notes |
|---|---|---|---|
| `state` | `str` | `"AZ"` or `"az"` | Two-letter state abbreviation |
| `month` | `int` | `4` | 1–12 |
| `year` | `int` | `2020` | Must be a year the Census population dataset covers |

It calls the Census API for county population and land area. It then:
- adds each county's name and land area to `counties`, skipping counties already stored;
- adds each county's population and population density to `county_demographic`, dated the 1st of the month (for example `2020-04-01`).

If that state and month are already loaded, it prints a message and does not call the API.

### `load_covid19_data(year)`

Downloads the NYT county file for one year and loads it into `covid`.

| Argument | Type | Allowed values |
|---|---|---|
| `year` | `int` | `2020`, `2021`, `2022`, `2023` |

Rows without a FIPS code (for example "Unknown" counties and New York City) are skipped. Each file has hundreds of thousands of rows, so this takes a while.

### Duplicate rows

All inserts go through `insert_many()`. A row that already exists (a UNIQUE constraint failure) is skipped and printed, and the rest of the rows are still inserted. Any other error, such as a missing required value, stops the insert, undoes it, and raises a `RuntimeError` that shows the query and the row that failed.

## Querying the database with `sqlite3`

Open the database from the project root:

```bash
sqlite3 database/covid.db
```

Useful commands at the `sqlite>` prompt:

```sql
.tables                       -- list all tables
.schema counties              -- show a table's columns
.headers on                   -- show column names in results
.mode column                  -- line results up in columns

SELECT * FROM states LIMIT 5;

-- Arizona counties with their population density in April 2020
SELECT c.county_name, d.population, d.population_density
FROM counties c
JOIN county_demographic d
  ON c.county_fips = d.county_fips AND c.state_fips = d.state_fips
WHERE c.state_fips = '04' AND d.date = '2020-04-01';

.quit                         -- exit
```

macOS includes `sqlite3`. On other systems, install it from https://sqlite.org/download.html or your package manager.

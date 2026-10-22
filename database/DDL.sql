--  still in progress
CREATE TABLE IF NOT EXISTS states(
    state_fips              VARCHAR NOT NULL,
    state_name              VARCHAR NOT NULL,
    PRIMARY KEY             (state_fips)
);

CREATE TABLE IF NOT EXISTS counties(
    county_fips             VARCHAR NOT NULL,
    state_fips              VARCHAR NOT NULL,
    county_name             VARCHAR,
    area_sq_km              FLOAT,
    PRIMARY KEY             (county_fips, state_fips),
    FOREIGN KEY             (state_fips) REFERENCES states(state_fips)
);

CREATE TABLE IF NOT EXISTS county_demographic(
    county_fips             VARCHAR NOT NULL,
    state_fips              VARCHAR NOT NULL,
    population              INTEGER,
    population_density      FLOAT,
    date                    DATETIME NOT NULL,
    PRIMARY KEY             (county_fips, state_fips, date),
    FOREIGN KEY             (county_fips, state_fips) REFERENCES counties(county_fips, state_fips)
);

CREATE TABLE IF NOT EXISTS covid(
    county_fips             VARCHAR NOT NULL,
    state_fips              VARCHAR NOT NULL,
    date                    DATETIME NOT NULL,
    cases                   INTEGER,
    deaths                  INTEGER,
    PRIMARY KEY             (county_fips, state_fips, date),
    FOREIGN KEY             (county_fips, state_fips) REFERENCES counties(county_fips, state_fips)
)


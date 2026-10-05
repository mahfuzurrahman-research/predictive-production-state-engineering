CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS qa;

CREATE OR REPLACE TABLE staging.release_value (
    region VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    release_step INTEGER NOT NULL,
    release_date DATE NOT NULL,
    value DOUBLE NOT NULL
);

CREATE OR REPLACE TABLE core.forecast_pair (
    region VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    origin_step INTEGER NOT NULL,
    target_step INTEGER NOT NULL,
    origin_date DATE NOT NULL,
    target_date DATE NOT NULL,
    actual DOUBLE NOT NULL,
    baseline DOUBLE NOT NULL,
    adaptive DOUBLE NOT NULL,
    PRIMARY KEY(region, product, origin_step, target_step)
);

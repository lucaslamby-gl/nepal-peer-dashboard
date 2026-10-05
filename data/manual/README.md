# Manual inputs

Two series have no public API. Drop CSVs here and rerun `scripts/01_pull_data.py`.

## eci.csv  (Growth Lab Atlas of Economic Complexity)
Columns: `iso3,year,eci,eci_rank`
Countries: NPL,BGD,BTN,IND,PAK,LKA,VNM,KHM,LAO (plus any SAARC member if you want a regional mean; none is computed for ECI).
Years: 2004 onward.

## emigrant_stock.csv  (UN DESA International Migrant Stock 2024, by origin)
Either `iso3,year,emigrants` (absolute stock abroad; the script divides by WDI population)
or `iso3,year,emigrants_pct` (already as % of origin population).
Years available in the source: 2005, 2010, 2015, 2020, 2024.

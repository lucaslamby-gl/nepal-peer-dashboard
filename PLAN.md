# Nepal Peer Comparison Dashboard: Plan

*Agreed 4 October 2026.*

## Purpose

A single shareable web page that shows how Nepal has moved over the last twenty years on roughly 45 high-level indicators, against a togglable set of peers and the South Asia regional average.

## Scope decisions

| Item | Decision |
|---|---|
| Countries | Nepal plus 8 peers: Bangladesh, Bhutan, India, Pakistan, Sri Lanka (South Asian neighbours); Vietnam, Cambodia, Lao PDR (aspirational / structural peers). Afghanistan and Maldives excluded (data gaps; Maldives is a small island tourism economy). Each peer can be switched off; Nepal is always on. |
| Regional reference | World Bank South Asia aggregate (code SAS), drawn as a dashed grey line. For IMF and UNDP series, which have no SAS aggregate, a GDP- or population-weighted mean of the eight SAARC members is computed and labelled as such. |
| Period | 2004 to latest available year, annual. One-off pull; rerun script to refresh. Pull date shown on the page. |
| Views | Levels (default) and index 2004 = 100 toggle. |
| Layout | Four tabs (Macro, Economic structure, Education, Socioeconomic). One line chart per indicator, Nepal highlighted, peers in fixed colours, SA dashed. Unified hover tooltip, source note under each chart. |
| Format | Static page: Python pulls data to JSON, one HTML page with Plotly charts, served from `/docs` on GitHub Pages. New repo `lucaslamby-gl/nepal-peer-dashboard`. |
| ECI | No public API. Pipeline reads `data/manual/eci.csv` (columns: iso3, year, eci, eci_rank). User fills from Atlas / Growth Lab data. |

## Indicators

### Macro (14)
GDP per capita PPP (const. 2021 $); real GDP growth; GDP per capita growth; GNI per capita Atlas; remittances % GDP; exports % GDP; imports % GDP; current account % GDP; FDI inflows % GDP; reserves in months of imports; general government gross debt % GDP (IMF WEO); general government balance % GDP (IMF WEO); general government revenue % GDP (IMF WEO); CPI inflation; gross fixed capital formation % GDP; gross savings % GDP; domestic credit to private sector % GDP.

### Economic structure (14)
Agriculture, industry, manufacturing, services value added % GDP; employment shares in agriculture, industry, services (ILO modelled); Economic Complexity Index and rank (Atlas, manual CSV); goods exports % GDP; services exports % GDP; high-tech exports % of manufactured exports; GDP per person employed; labour force participation; unemployment; informal employment share; electricity access; electricity consumption per capita; mobile subscriptions per 100; internet users %; Logistics Performance Index.

### Education (6)
Mean years of schooling and expected years of schooling (UNDP HDR); gross secondary enrolment; gross tertiary enrolment; Human Capital Index; learning-adjusted years of schooling; adult literacy.

### Socioeconomic (12)
Poverty headcount at the international poverty line and the lower-middle-income line; Gini; income share of bottom 40%; life expectancy; under-5 mortality; fertility; age dependency ratio; urban population share; net migration; international migrant stock abroad % population (UN DESA, 5-yearly); remittances received per capita.

## Sources
- World Bank WDI API (v2, JSON) for most series, including ILO modelled labour series and the SAS aggregate.
- IMF WEO via DataMapper API for debt, balance, revenue.
- UNDP HDR composite indices time-series CSV for schooling.
- UN DESA International Migrant Stock 2024 for emigrant stock.
- Growth Lab Atlas for ECI (manual).

## Build steps
1. `scripts/01_pull_data.py`: fetch all series, compute derived series and weighted SA means, write `docs/data/indicators.json` and `data/indicators_long.csv`.
2. `docs/index.html`: tabs, peer toggles, level/index toggle, Plotly charts, source notes, pull date.
3. Preview locally, screenshot check.
4. `git init`, create GitHub repo, push, enable Pages from `/docs`.

## Known gaps
- Human Capital Index exists only for 2010, 2017, 2018, 2020.
- WDI electricity consumption per capita ends around 2014 for most countries.
- Migrant stock is 5-yearly (2005 to 2020) plus 2024.
- Informal employment share has sparse coverage.

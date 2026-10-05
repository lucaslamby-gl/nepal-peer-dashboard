# Nepal Peer Dashboard

Interactive comparison of Nepal with South Asian neighbours (Bangladesh, Bhutan, India, Pakistan, Sri Lanka), structural peers (Vietnam, Cambodia, Lao PDR) and the World Bank South Asia aggregate on ~45 indicators, 2004 to latest.

Live page: https://lucaslamby-gl.github.io/nepal-peer-dashboard/

## Structure
- `scripts/01_pull_data.py` pulls World Bank WDI, IMF WEO / Fiscal Monitor and UNDP HDR series, computes derived series and weighted South Asia means, and writes `docs/data/indicators.json` plus `data/indicators_long.csv`.
- `docs/index.html` is the static page (Plotly), served by GitHub Pages from `/docs`.
- `data/manual/` holds inputs with no public API (ECI from the Atlas, emigrant stock from UN DESA). See its README.
- `PLAN.md` records the scope decisions.

## Refresh
```
uv venv .venv --python 3.12
uv pip install --python .venv/Scripts/python.exe pandas requests openpyxl
.venv/Scripts/python.exe scripts/01_pull_data.py
```
Then commit and push; the page shows the pull date.

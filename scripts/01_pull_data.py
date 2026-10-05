"""
Pull indicator time series for Nepal, peers and the South Asia aggregate.

Sources
- World Bank WDI API v2 (most series, incl. ILO modelled labour series and SAS aggregate)
- IMF WEO via DataMapper API (government debt, balance, revenue)
- UNDP HDR composite indices CSV (mean and expected years of schooling)
- Manual CSVs in data/manual/ (ECI from the Atlas; emigrant stock from UN DESA)

Outputs
- docs/data/indicators.json   (consumed by docs/index.html)
- data/indicators_long.csv    (tidy long table for analysis)

Run:  .venv/Scripts/python.exe scripts/01_pull_data.py
"""
from __future__ import annotations

import datetime as dt
import io
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "data" / "manual"
OUT_JSON = ROOT / "docs" / "data" / "indicators.json"
OUT_CSV = ROOT / "data" / "indicators_long.csv"

START_YEAR = 2004
END_YEAR = dt.date.today().year

COUNTRIES = {
    "NPL": "Nepal",
    "BGD": "Bangladesh",
    "BTN": "Bhutan",
    "IND": "India",
    "PAK": "Pakistan",
    "LKA": "Sri Lanka",
    "VNM": "Vietnam",
    "KHM": "Cambodia",
    "LAO": "Lao PDR",
}
REGION = {"SAS": "South Asia"}
# Members used to compute a weighted South Asia mean when a source has no SAS aggregate
SAARC = ["AFG", "BGD", "BTN", "IND", "MDV", "NPL", "PAK", "LKA"]

GROUPS = {
    "macro": "Macroeconomic",
    "structure": "Economic structure",
    "education": "Education",
    "social": "Socioeconomic",
}

# id, group, label, unit, source_type, source_code, note
# unit tags: usd, pct, pct_gdp, index, years, number, per100, months, rate, rank
WDI = [
    # --- Macro
    ("gdp_pc_ppp", "macro", "GDP per capita, PPP", "const. 2021 intl $", "NY.GDP.PCAP.PP.KD", ""),
    ("gdp_growth", "macro", "Real GDP growth", "% per year", "NY.GDP.MKTP.KD.ZG", ""),
    ("gdp_pc_growth", "macro", "GDP per capita growth", "% per year", "NY.GDP.PCAP.KD.ZG", ""),
    ("gni_pc_atlas", "macro", "GNI per capita, Atlas method", "current US$", "NY.GNP.PCAP.CD", ""),
    ("remit_gdp", "macro", "Personal remittances received", "% of GDP", "BX.TRF.PWKR.DT.GD.ZS", ""),
    ("exports_gdp", "macro", "Exports of goods and services", "% of GDP", "NE.EXP.GNFS.ZS", ""),
    ("imports_gdp", "macro", "Imports of goods and services", "% of GDP", "NE.IMP.GNFS.ZS", ""),
    ("ca_gdp", "macro", "Current account balance", "% of GDP", "BN.CAB.XOKA.GD.ZS", ""),
    ("fdi_gdp", "macro", "FDI net inflows", "% of GDP", "BX.KLT.DINV.WD.GD.ZS", ""),
    ("reserves_months", "macro", "Total reserves", "months of imports", "FI.RES.TOTL.MO", ""),
    ("inflation", "macro", "Inflation, consumer prices", "% per year", "FP.CPI.TOTL.ZG", ""),
    ("gfcf_gdp", "macro", "Gross fixed capital formation", "% of GDP", "NE.GDI.FTOT.ZS", ""),
    ("savings_gdp", "macro", "Gross savings", "% of GDP", "NY.GNS.ICTR.ZS", ""),
    ("credit_gdp", "macro", "Domestic credit to private sector", "% of GDP", "FS.AST.PRVT.GD.ZS", ""),
    # --- Structure
    ("va_agr", "structure", "Agriculture value added", "% of GDP", "NV.AGR.TOTL.ZS", ""),
    ("va_ind", "structure", "Industry value added (incl. construction)", "% of GDP", "NV.IND.TOTL.ZS", ""),
    ("va_manf", "structure", "Manufacturing value added", "% of GDP", "NV.IND.MANF.ZS", ""),
    ("va_srv", "structure", "Services value added", "% of GDP", "NV.SRV.TOTL.ZS", ""),
    ("emp_agr", "structure", "Employment in agriculture", "% of employment", "SL.AGR.EMPL.ZS", "ILO modelled estimates"),
    ("emp_ind", "structure", "Employment in industry", "% of employment", "SL.IND.EMPL.ZS", "ILO modelled estimates"),
    ("emp_srv", "structure", "Employment in services", "% of employment", "SL.SRV.EMPL.ZS", "ILO modelled estimates"),
    ("hitech_exp", "structure", "High-technology exports", "% of manufactured exports", "TX.VAL.TECH.MF.ZS", ""),
    ("gdp_per_worker", "structure", "GDP per person employed", "const. 2021 PPP $", "SL.GDP.PCAP.EM.KD", "ILO modelled estimates"),
    ("lfpr", "structure", "Labour force participation rate, 15+", "% of population 15+", "SL.TLF.CACT.ZS", "ILO modelled estimates"),
    ("unemp", "structure", "Unemployment rate", "% of labour force", "SL.UEM.TOTL.ZS", "ILO modelled estimates"),
    ("elec_access", "structure", "Access to electricity", "% of population", "EG.ELC.ACCS.ZS", ""),
    ("elec_use_pc", "structure", "Electric power consumption per capita", "kWh", "EG.USE.ELEC.KH.PC", "WDI series ends around 2014"),
    ("mobile", "structure", "Mobile cellular subscriptions", "per 100 people", "IT.CEL.SETS.P2", ""),
    ("internet", "structure", "Individuals using the Internet", "% of population", "IT.NET.USER.ZS", ""),
    ("lpi", "structure", "Logistics Performance Index, overall", "score 1 to 5", "LP.LPI.OVRL.XQ", "survey years only"),
    # --- Education
    ("sec_enrol", "education", "School enrolment, secondary (gross)", "%", "SE.SEC.ENRR", ""),
    ("ter_enrol", "education", "School enrolment, tertiary (gross)", "%", "SE.TER.ENRR", ""),
    ("hci", "education", "Human Capital Index", "scale 0 to 1", "HD.HCI.OVRL", "2010, 2017, 2018, 2020 only"),
    ("lays", "education", "Learning-adjusted years of school", "years", "HD.HCI.LAYS", "2010, 2017, 2018, 2020 only"),
    ("literacy", "education", "Literacy rate, adult total", "% of people 15+", "SE.ADT.LITR.ZS", "census/survey years only"),
    # --- Social
    ("pov_ipl", "social", "Poverty headcount at the international poverty line", "% of population", "SI.POV.DDAY", "survey years; $3.00/day 2021 PPP"),
    ("pov_lmic", "social", "Poverty headcount at the lower-middle-income line", "% of population", "SI.POV.LMIC", "survey years; $4.20/day 2021 PPP"),
    ("gini", "social", "Gini index", "0 to 100", "SI.POV.GINI", "survey years"),
    ("life_exp", "social", "Life expectancy at birth", "years", "SP.DYN.LE00.IN", ""),
    ("u5_mort", "social", "Under-5 mortality rate", "per 1,000 live births", "SH.DYN.MORT", ""),
    ("fertility", "social", "Fertility rate, total", "births per woman", "SP.DYN.TFRT.IN", ""),
    ("dependency", "social", "Age dependency ratio", "% of working-age population", "SP.POP.DPND", ""),
    ("urban", "social", "Urban population", "% of total", "SP.URB.TOTL.IN.ZS", ""),
    ("net_migration", "social", "Net migration", "persons", "SM.POP.NETM", "UN WPP via WDI"),
]

# Helper series needed for derived indicators (not shown directly)
WDI_HELPERS = [
    ("_gdp_usd", "NY.GDP.MKTP.CD"),
    ("_pop", "SP.POP.TOTL"),
    ("_remit_usd", "BX.TRF.PWKR.CD.DT"),
    ("_goods_exp_usd", "BX.GSR.MRCH.CD"),
    ("_serv_exp_usd", "BX.GSR.NFSV.CD"),
    ("_inc_q1", "SI.DST.FRST.20"),
    ("_inc_q2", "SI.DST.02ND.20"),
]

IMF = [
    ("gov_debt", "macro", "General government gross debt", "% of GDP", "GGXWDG_NGDP", "IMF WEO; SA mean is GDP-weighted"),
    ("gov_balance", "macro", "General government net lending/borrowing", "% of GDP", "GGXCNL_NGDP", "IMF WEO; SA mean is GDP-weighted"),
    ("gov_revenue", "macro", "General government revenue", "% of GDP", "GGR_G01_GDP_PT", "IMF Fiscal Monitor; SA mean is GDP-weighted"),
]

HDR = [
    ("mys", "education", "Mean years of schooling, 25+", "years", "mys", "UNDP HDR 2025; SA mean is population-weighted"),
    ("eys", "education", "Expected years of schooling", "years", "eys", "UNDP HDR 2025; SA mean is population-weighted"),
]

DERIVED = [
    ("goods_exp_gdp", "structure", "Goods exports", "% of GDP", "", "BX.GSR.MRCH.CD / NY.GDP.MKTP.CD"),
    ("serv_exp_gdp", "structure", "Services exports", "% of GDP", "", "BX.GSR.NFSV.CD / NY.GDP.MKTP.CD"),
    ("bottom40", "social", "Income share held by bottom 40%", "% of income", "", "SI.DST.FRST.20 + SI.DST.02ND.20; survey years"),
    ("remit_pc", "social", "Remittances received per capita", "current US$", "", "BX.TRF.PWKR.CD.DT / SP.POP.TOTL"),
]

MANUAL_FILES = [
    ("eci", "structure", "Economic Complexity Index", "index", "eci.csv", "Growth Lab Atlas; manual CSV"),
    ("eci_rank", "structure", "Economic Complexity ranking", "rank (1 = most complex)", "eci.csv", "Growth Lab Atlas; manual CSV"),
    ("emigrants_pct", "social", "Emigrant stock abroad", "% of population", "emigrant_stock.csv", "UN DESA IMS 2024; manual CSV; 5-yearly"),
]

SESSION = requests.Session()
# IMF DataMapper rejects browser-like user agents; keep the default python-requests UA


def get_json(url: str, params: dict | None = None, tries: int = 4):
    for i in range(tries):
        try:
            r = SESSION.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))
            print(f"  retry {i+1} for {url}: {e}", file=sys.stderr)


# ---------------------------------------------------------------- World Bank
def wdi_series(code: str, isos: list[str]) -> pd.DataFrame:
    url = f"https://api.worldbank.org/v2/country/{';'.join(isos)}/indicator/{code}"
    rows = []
    page = 1
    while True:
        js = get_json(url, {"format": "json", "date": f"{START_YEAR}:{END_YEAR}", "per_page": 1000, "page": page})
        if not isinstance(js, list) or len(js) < 2 or js[1] is None:
            break
        for o in js[1]:
            if o["value"] is not None:
                rows.append((o["countryiso3code"], int(o["date"]), float(o["value"])))
        if page >= js[0]["pages"]:
            break
        page += 1
    return pd.DataFrame(rows, columns=["iso3", "year", "value"])


# ---------------------------------------------------------------- IMF WEO
def imf_series(code: str) -> pd.DataFrame:
    js = get_json(f"https://www.imf.org/external/datamapper/api/v1/{code}")
    vals = js["values"][code]
    rows = []
    for iso, years in vals.items():
        for y, v in years.items():
            y = int(y)
            if START_YEAR <= y <= END_YEAR and v is not None:
                rows.append((iso, y, float(v)))
    return pd.DataFrame(rows, columns=["iso3", "year", "value"])


# ---------------------------------------------------------------- UNDP HDR
def hdr_table() -> pd.DataFrame:
    url = "https://hdr.undp.org/sites/default/files/2025_HDR/HDR25_Composite_indices_complete_time_series.csv"
    r = SESSION.get(url, timeout=120)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.content.decode("utf-8", errors="replace")))
    long = df.melt(id_vars=["iso3"], var_name="var", value_name="value").dropna()
    long = long[long["var"].str.match(r"^(mys|eys)_\d{4}$")]
    long["key"] = long["var"].str[:3]
    long["year"] = long["var"].str[-4:].astype(int)
    long = long[(long["year"] >= START_YEAR)]
    return long[["key", "iso3", "year", "value"]]


# ---------------------------------------------------------------- helpers
def weighted_region(df: pd.DataFrame, weights: pd.DataFrame, label: str = "SAS") -> pd.DataFrame:
    """Weighted mean over SAARC members for each year; requires at least 5 members incl. IND."""
    m = df[df["iso3"].isin(SAARC)].merge(weights, on=["iso3", "year"], suffixes=("", "_w"))
    out = []
    for y, g in m.groupby("year"):
        if len(g) >= 5 and "IND" in set(g["iso3"]):
            out.append((label, y, float((g["value"] * g["value_w"]).sum() / g["value_w"].sum())))
    return pd.DataFrame(out, columns=["iso3", "year", "value"])


def read_manual(fname: str, col: str) -> pd.DataFrame:
    p = MANUAL / fname
    if not p.exists():
        return pd.DataFrame(columns=["iso3", "year", "value"])
    df = pd.read_csv(p)
    df.columns = [c.strip().lower() for c in df.columns]
    if col not in df.columns:
        return pd.DataFrame(columns=["iso3", "year", "value"])
    df = df.rename(columns={col: "value"})[["iso3", "year", "value"]].dropna()
    df["year"] = df["year"].astype(int)
    df["value"] = df["value"].astype(float)
    return df


# ---------------------------------------------------------------- main
def main() -> None:
    isos = list(COUNTRIES) + list(REGION)
    isos_all = sorted(set(isos + SAARC))
    frames: dict[str, pd.DataFrame] = {}
    meta: dict[str, dict] = {}

    print("World Bank WDI ...")
    for key, group, label, unit, code, note in WDI:
        df = wdi_series(code, isos)
        frames[key] = df
        meta[key] = dict(group=group, label=label, unit=unit, source="World Bank WDI", code=code, note=note)
        print(f"  {key:16s} {len(df):4d} obs  latest {df['year'].max() if len(df) else '-'}")

    helpers: dict[str, pd.DataFrame] = {}
    for key, code in WDI_HELPERS:
        helpers[key] = wdi_series(code, isos_all)
        print(f"  {key:16s} {len(helpers[key]):4d} obs")

    gdp_w = helpers["_gdp_usd"].rename(columns={"value": "value_w"})[["iso3", "year", "value_w"]]
    pop_w = helpers["_pop"].rename(columns={"value": "value_w"})[["iso3", "year", "value_w"]]

    print("IMF WEO ...")
    for key, group, label, unit, code, note in IMF:
        df = imf_series(code)
        # drop WEO projections beyond the latest actual year (use current year - 1 as cutoff)
        df = df[df["year"] <= dt.date.today().year - 1]
        reg = weighted_region(df, gdp_w)
        df = pd.concat([df[df["iso3"].isin(COUNTRIES)], reg], ignore_index=True)
        frames[key] = df
        meta[key] = dict(group=group, label=label, unit=unit, source="IMF WEO (DataMapper)", code=code, note=note)
        print(f"  {key:16s} {len(df):4d} obs")

    print("UNDP HDR ...")
    hdr = hdr_table()
    for key, group, label, unit, col, note in HDR:
        df = hdr[hdr["key"] == col][["iso3", "year", "value"]]
        reg = weighted_region(df, pop_w)
        df = pd.concat([df[df["iso3"].isin(COUNTRIES)], reg], ignore_index=True)
        frames[key] = df
        meta[key] = dict(group=group, label=label, unit=unit, source="UNDP Human Development Report 2025", code=col, note=note)
        print(f"  {key:16s} {len(df):4d} obs")

    print("Derived ...")
    def ratio(num: str, den: str, scale: float) -> pd.DataFrame:
        m = helpers[num].merge(helpers[den], on=["iso3", "year"], suffixes=("_n", "_d"))
        m["value"] = m["value_n"] / m["value_d"] * scale
        return m[m["iso3"].isin(isos)][["iso3", "year", "value"]]

    frames["goods_exp_gdp"] = ratio("_goods_exp_usd", "_gdp_usd", 100)
    frames["serv_exp_gdp"] = ratio("_serv_exp_usd", "_gdp_usd", 100)
    frames["remit_pc"] = ratio("_remit_usd", "_pop", 1)
    m = helpers["_inc_q1"].merge(helpers["_inc_q2"], on=["iso3", "year"], suffixes=("_1", "_2"))
    m["value"] = m["value_1"] + m["value_2"]
    frames["bottom40"] = m[m["iso3"].isin(isos)][["iso3", "year", "value"]]
    for key, group, label, unit, _, note in DERIVED:
        meta[key] = dict(group=group, label=label, unit=unit, source="World Bank WDI (derived)", code="", note=note)
        print(f"  {key:16s} {len(frames[key]):4d} obs")

    print("Manual CSVs ...")
    for key, group, label, unit, fname, note in MANUAL_FILES:
        col = key if key != "emigrants_pct" else "emigrants_pct"
        df = read_manual(fname, col)
        if key == "emigrants_pct" and len(df) == 0:
            # allow absolute stock + compute share using WDI population
            stock = read_manual(fname, "emigrants")
            if len(stock):
                m = stock.merge(helpers["_pop"], on=["iso3", "year"], suffixes=("", "_pop"))
                m["value"] = m["value"] / m["value_pop"] * 100
                df = m[["iso3", "year", "value"]]
        frames[key] = df[df["iso3"].isin(isos)] if len(df) else df
        meta[key] = dict(group=group, label=label, unit=unit, source=note.split(";")[0], code=fname, note=note)
        status = f"{len(frames[key])} obs" if len(frames[key]) else "MISSING (add data/manual/%s)" % fname
        print(f"  {key:16s} {status}")

    # ------------------------------------------------------------ assemble
    order = [k for k, *_ in WDI] + [k for k, *_ in IMF] + [k for k, *_ in HDR] + [k for k, *_ in DERIVED] + [k for k, *_ in MANUAL_FILES]
    # place ECI right after sector shares, migration items at the end of social
    order.remove("eci"); order.remove("eci_rank")
    i = order.index("emp_srv") + 1
    order[i:i] = ["eci", "eci_rank"]

    long_rows = []
    series_out = {}
    for key in order:
        df = frames[key]
        df = df[(df["year"] >= START_YEAR) & (df["year"] <= END_YEAR)]
        series_out[key] = {
            iso: {int(y): round(float(v), 4) for y, v in g.sort_values("year")[["year", "value"]].values}
            for iso, g in df.groupby("iso3")
        }
        for iso, y, v in df[["iso3", "year", "value"]].values:
            long_rows.append((key, iso, int(y), float(v)))

    payload = {
        "generated": dt.date.today().isoformat(),
        "start_year": START_YEAR,
        "countries": COUNTRIES,
        "region": REGION,
        "groups": GROUPS,
        "order": order,
        "meta": meta,
        "series": series_out,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    pd.DataFrame(long_rows, columns=["indicator", "iso3", "year", "value"]).to_csv(OUT_CSV, index=False)
    print(f"\nWrote {OUT_JSON} ({OUT_JSON.stat().st_size/1024:.0f} KB) and {OUT_CSV}")


if __name__ == "__main__":
    main()

"""
Discogs Desire Index — Streamlit front end.

Reads LIVE from the DuckDB gold layer (main.fct_release + dimensions) produced by
dbt. No CSV exports — the app queries the warehouse directly, which is the
required pattern for the assessment.

Run from the `pipeline` folder:
    streamlit run app.py
"""

import os
import duckdb
import pandas as pd
import streamlit as st

# --- DB path: resolve next to this file so it works regardless of where you run it ---
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "discogs.duckdb")

LABEL_NAMES = {
    "felt": "FELT",
    "motion_ward": "Motion Ward",
    "year0001": "Year0001",
    "posh_isolation": "Posh Isolation",
}

st.set_page_config(page_title="Discogs Desire Index", page_icon="🎛️", layout="wide")


# ---------------------------------------------------------------- data access
@st.cache_data(ttl=300)
def load_releases() -> pd.DataFrame:
    """One denormalised row per release, joined across the star schema."""
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute(
        """
        select
            f.release_id,
            f.release_title,
            f.source_label,
            la.label_name,
            ar.artist_name,
            fm.format_name,
            fm.format_class,
            d.release_year,
            f.country,
            f.community_have      as have,
            f.community_want      as want,
            f.num_for_sale,
            f.rating_average      as rating,
            f.want_to_have_ratio  as ratio,
            coalesce(g.genres, '') as genres
        from main.fct_release f
        left join main.dim_label  la on f.label_key  = la.label_key
        left join main.dim_artist ar on f.artist_key = ar.artist_key
        left join main.dim_format fm on f.format_key = fm.format_key
        left join main.dim_date   d  on f.year_key   = d.year_key
        left join (
            select release_id, string_agg(genre_name, ', ' order by genre_name) as genres
            from main.bridge_release_genre
            group by release_id
        ) g on f.release_id = g.release_id
        """
    ).df()
    con.close()
    return df


@st.cache_data(ttl=300)
def load_health() -> pd.DataFrame:
    """Per-label data-health summary (observability panel)."""
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute(
        """
        select
            source_label,
            count(*)                                                   as releases,
            round(100.0 * count(release_year)      / count(*), 1)      as pct_with_year,
            round(100.0 * count(case when community_have > 0 then 1 end)
                        / count(*), 1)                                 as pct_with_demand_data,
            max(source_loaded_at)                                      as last_loaded
        from main.fct_release
        left join main.dim_date using (year_key)
        group by source_label
        order by releases desc
        """
    ).df()
    con.close()
    return df


# ---------------------------------------------------------------- load + guard
try:
    df = load_releases()
except Exception as e:
    st.error(
        "Couldn't read the warehouse. Make sure you've run `dbt build` and that "
        f"`discogs.duckdb` sits next to this app.\n\nDetails: {e}"
    )
    st.stop()

df["label_pretty"] = df["source_label"].map(LABEL_NAMES).fillna(df["source_label"])
df["genre_list"] = df["genres"].apply(lambda s: [g.strip() for g in s.split(",") if g.strip()])

# ---------------------------------------------------------------- header
st.title("🎛️ Discogs Desire Index")
st.caption(
    "Desire vs ownership across four independent labels — which records are most "
    "coveted but least owned. Data flows live from the Discogs API → DuckDB → dbt → here."
)

# ---------------------------------------------------------------- sidebar filters
st.sidebar.header("Filters")

label_opts = sorted(df["label_pretty"].unique())
sel_labels = st.sidebar.multiselect("Label", label_opts, default=label_opts)

class_opts = sorted(df["format_class"].dropna().unique())
sel_class = st.sidebar.multiselect("Format type", class_opts, default=class_opts)

all_genres = sorted({g for lst in df["genre_list"] for g in lst})
sel_genres = st.sidebar.multiselect("Genre (any of)", all_genres, default=[])

min_owners = st.sidebar.slider(
    "Minimum owners (have)", 0, 50, 0,
    help="Raise this to filter out extreme ratios that come from just 1–2 owners.",
)

years = df["release_year"].dropna()
if len(years):
    y_min, y_max = int(years.min()), int(years.max())
    yr = st.sidebar.slider("Release year", y_min, y_max, (y_min, y_max))
else:
    yr = None

# ---------------------------------------------------------------- apply filters
mask = (
    df["label_pretty"].isin(sel_labels)
    & df["format_class"].isin(sel_class)
    & (df["have"].fillna(0) >= min_owners)
)
if sel_genres:
    mask &= df["genre_list"].apply(lambda lst: any(g in lst for g in sel_genres))
if yr is not None:
    mask &= df["release_year"].isna() | df["release_year"].between(yr[0], yr[1])

fdf = df[mask].copy()

# ---------------------------------------------------------------- KPI row
c1, c2, c3, c4 = st.columns(4)
c1.metric("Releases", f"{len(fdf):,}")
c2.metric("Total wanting", f"{int(fdf['want'].fillna(0).sum()):,}")
c3.metric("Total owning", f"{int(fdf['have'].fillna(0).sum()):,}")
med = fdf.loc[fdf["have"].fillna(0) > 0, "ratio"].median()
c4.metric("Median want/have", f"{med:.1f}" if pd.notna(med) else "—")

st.divider()

# ---------------------------------------------------------------- tabs
tab_browse, tab_wanted, tab_format, tab_label, tab_health = st.tabs(
    ["📀 Browse", "🔥 Most wanted", "💿 Physical vs digital", "🏷️ By label", "🩺 Data health"]
)

with tab_browse:
    st.subheader("Browse the catalogue")
    sort_col = st.selectbox(
        "Sort by", ["want/have ratio", "want", "have", "for sale", "year"], index=0
    )
    sort_map = {"want/have ratio": "ratio", "want": "want", "have": "have",
                "for sale": "num_for_sale", "year": "release_year"}
    view = fdf.sort_values(sort_map[sort_col], ascending=False, na_position="last")[
        ["release_title", "artist_name", "label_pretty", "format_name",
         "release_year", "genres", "have", "want", "ratio", "num_for_sale"]
    ].rename(columns={
        "release_title": "Title", "artist_name": "Artist", "label_pretty": "Label",
        "format_name": "Format", "release_year": "Year", "genres": "Genres",
        "have": "Have", "want": "Want", "ratio": "Want/Have", "num_for_sale": "For sale",
    })
    st.dataframe(view, use_container_width=True, hide_index=True, height=520)
    st.caption(f"{len(view):,} releases shown.")

with tab_wanted:
    st.subheader("Most coveted (highest want-to-have ratio)")
    top = (fdf[fdf["have"].fillna(0) > 0]
           .sort_values("ratio", ascending=False)
           .head(15)
           .assign(label_disp=lambda d: d["release_title"] + " — " + d["label_pretty"]))
    if len(top):
        chart_df = top.set_index("label_disp")[["ratio"]].rename(columns={"ratio": "Want/Have"})
        st.bar_chart(chart_df, horizontal=True, height=480)
        st.caption(
            "Tip: raise the *Minimum owners* filter in the sidebar to see robust "
            "ratios (big numbers) rather than extremes from 1–2 owners."
        )
    else:
        st.info("No releases match the current filters.")

with tab_format:
    st.subheader("Physical vs digital")
    g = (fdf.groupby("format_class")
            .agg(releases=("release_id", "count"),
                 total_want=("want", "sum"),
                 avg_ratio=("ratio", "mean"))
            .reset_index())
    cc1, cc2 = st.columns(2)
    with cc1:
        st.bar_chart(g.set_index("format_class")[["releases"]], height=320)
        st.caption("Number of releases by format type.")
    with cc2:
        st.bar_chart(g.set_index("format_class")[["avg_ratio"]], height=320)
        st.caption("Average want/have ratio by format type.")
    st.dataframe(g.rename(columns={
        "format_class": "Format type", "releases": "Releases",
        "total_want": "Total want", "avg_ratio": "Avg want/have"}),
        use_container_width=True, hide_index=True)

with tab_label:
    st.subheader("Per-label comparison")
    g = (fdf.groupby("label_pretty")
            .agg(releases=("release_id", "count"),
                 total_have=("have", "sum"),
                 total_want=("want", "sum"),
                 avg_ratio=("ratio", "mean"))
            .reset_index())
    st.bar_chart(g.set_index("label_pretty")[["avg_ratio"]], height=320)
    st.caption("Average want/have ratio by label — which label's catalogue is most coveted.")
    st.dataframe(g.rename(columns={
        "label_pretty": "Label", "releases": "Releases", "total_have": "Total have",
        "total_want": "Total want", "avg_ratio": "Avg want/have"}),
        use_container_width=True, hide_index=True)

with tab_health:
    st.subheader("Pipeline data health")
    st.caption(
        "Observability panel: how complete the data is per label, and when it was "
        "last loaded. Inspired by waxindex's data-health view."
    )
    try:
        h = load_health()
        h["source_label"] = h["source_label"].map(LABEL_NAMES).fillna(h["source_label"])
        st.dataframe(h.rename(columns={
            "source_label": "Label", "releases": "Releases",
            "pct_with_year": "% with year", "pct_with_demand_data": "% with demand data",
            "last_loaded": "Last loaded"}),
            use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"Couldn't load health summary: {e}")

with st.expander("ℹ️ About this pipeline"):
    st.markdown(
        "- **Source:** Discogs API (releases for 4 independent labels)\n"
        "- **Ingestion:** Python script, rate-limit aware, lands raw JSON\n"
        "- **Raw / bronze:** `raw.releases_raw` in DuckDB (one row per release, untouched)\n"
        "- **Transform:** dbt — staging → intermediate → star schema (fact + dims), tested\n"
        "- **This app:** Streamlit, querying the gold layer live (no CSV export)"
    )

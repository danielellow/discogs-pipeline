"""
Grails — a crate-digger's desire index.

A discovery wall of the most-coveted, least-owned records across four independent
labels. Reads LIVE from the DuckDB gold layer (main.fct_release + dims) built by
dbt — no CSV exports.

Run from the `pipeline` folder:  streamlit run app.py
"""

import os
import html
import duckdb
import pandas as pd
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "discogs.duckdb")

LABEL_NAMES = {
    "felt": "FELT", "motion_ward": "Motion Ward",
    "year0001": "Year0001", "posh_isolation": "Posh Isolation",
}

st.set_page_config(page_title="Grails - a desire index", page_icon="🖤", layout="wide")


@st.cache_data(ttl=300)
def load_releases() -> pd.DataFrame:
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute(
        """
        select
            f.release_id, f.release_title, f.source_label,
            la.label_name, ar.artist_name,
            fm.format_name, fm.format_class,
            d.release_year, f.country,
            f.thumb_url, f.discogs_uri, f.styles,
            f.community_have as have, f.community_want as want,
            f.num_for_sale, f.rating_average as rating, f.want_to_have_ratio as ratio,
            coalesce(g.genres, '') as genres
        from main.fct_release f
        left join main.dim_label  la on f.label_key  = la.label_key
        left join main.dim_artist ar on f.artist_key = ar.artist_key
        left join main.dim_format fm on f.format_key = fm.format_key
        left join main.dim_date   d  on f.year_key   = d.year_key
        left join (
            select release_id, string_agg(genre_name, ', ' order by genre_name) as genres
            from main.bridge_release_genre group by release_id
        ) g on f.release_id = g.release_id
        """
    ).df()
    con.close()
    return df


@st.cache_data(ttl=300)
def load_health() -> pd.DataFrame:
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute(
        """
        select source_label,
               count(*) as releases,
               round(100.0*count(release_year)/count(*),1) as pct_with_year,
               round(100.0*count(case when community_have>0 then 1 end)/count(*),1) as pct_with_demand_data,
               max(source_loaded_at) as last_loaded
        from main.fct_release left join main.dim_date using (year_key)
        group by source_label order by releases desc
        """
    ).df()
    con.close()
    return df


st.markdown(
    """
    <style>
      .concept { color:#8a8a8a; font-size:1.02rem; line-height:1.5; max-width:60rem; }
      .wall { display:grid; grid-template-columns:repeat(auto-fill, minmax(150px,1fr));
              gap:14px; margin-top:8px; }
      .card { position:relative; text-decoration:none; color:inherit;
              border:1px solid #2a2a2a; border-radius:10px; overflow:hidden; background:#161616;
              transition:transform .12s ease, border-color .12s ease; display:block; }
      .card:hover { transform:translateY(-3px); border-color:#666; }
      .cover { width:100%; aspect-ratio:1/1; background:#222 center/cover no-repeat;
               display:flex; align-items:center; justify-content:center; color:#444; font-size:.7rem; }
      .badge { position:absolute; top:8px; left:8px; background:#e8482b; color:#fff;
               font-weight:700; font-size:.74rem; padding:2px 7px; border-radius:20px; }
      .meta { padding:9px 10px 11px; }
      .t { font-weight:600; font-size:.86rem; line-height:1.2; margin-bottom:2px;
           overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .a { color:#bdbdbd; font-size:.8rem; margin-bottom:6px;
           overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .s { color:#7d7d7d; font-size:.72rem; }
      .n { color:#9a9a9a; font-size:.72rem; margin-top:4px; }
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    df = load_releases()
except Exception as e:
    st.error(f"Couldn't read the warehouse. Run `dbt build` first.\n\nDetails: {e}")
    st.stop()

df["label_pretty"] = df["source_label"].map(LABEL_NAMES).fillna(df["source_label"])
df["genre_list"] = df["genres"].apply(lambda s: [g.strip() for g in s.split(",") if g.strip()])

st.title("🖤 Grails")
st.markdown(
    f"<div class='concept'>The records the underground <b>craves</b> but almost no one owns. "
    f"{len(df):,} releases across four independent labels - FELT, Motion Ward, Year0001 and "
    f"Posh Isolation - each ranked by <b>desire</b>: how many people want it for every one "
    f"person who has it. Higher = rarer and more coveted.</div>",
    unsafe_allow_html=True,
)
st.write("")

st.sidebar.header("Dig the crates")
label_opts = sorted(df["label_pretty"].unique())
sel_labels = st.sidebar.multiselect("Label", label_opts, default=label_opts)
class_opts = sorted(df["format_class"].dropna().unique())
sel_class = st.sidebar.multiselect("Format", class_opts, default=class_opts)
all_genres = sorted({g for lst in df["genre_list"] for g in lst})
sel_genres = st.sidebar.multiselect("Genre (any of)", all_genres, default=[])
min_owners = st.sidebar.slider(
    "Minimum owners", 0, 50, 3,
    help="Higher = robust grails (real demand). Lower = include extreme 1-2-owner rarities.",
)
years = df["release_year"].dropna()
yr = None
if len(years):
    y0, y1 = int(years.min()), int(years.max())
    yr = st.sidebar.slider("Year", y0, y1, (y0, y1))

mask = (
    df["label_pretty"].isin(sel_labels)
    & df["format_class"].isin(sel_class)
    & (df["have"].fillna(0) >= min_owners)
    & (df["ratio"].notna())
)
if sel_genres:
    mask &= df["genre_list"].apply(lambda lst: any(g in lst for g in sel_genres))
if yr is not None:
    mask &= df["release_year"].isna() | df["release_year"].between(yr[0], yr[1])
fdf = df[mask].copy().sort_values("ratio", ascending=False)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Records in view", f"{len(fdf):,}")
c2.metric("Total wanting", f"{int(fdf['want'].fillna(0).sum()):,}")
c3.metric("Total owning", f"{int(fdf['have'].fillna(0).sum()):,}")
md = fdf["ratio"].median()
c4.metric("Median desire", f"{md:.1f}x" if pd.notna(md) else "-")
st.divider()

tab_wall, tab_top, tab_fmt, tab_lab, tab_health = st.tabs(
    ["🧱 The wall", "🔥 Top grails", "💿 Physical vs digital", "🏷️ By label", "🩺 Data health"]
)

with tab_wall:
    st.caption("Sorted by desire. Click any sleeve to open it on Discogs.")
    show = fdf.head(90)
    if len(show) == 0:
        st.info("No records match the current filters - loosen them in the sidebar.")
    else:
        cards = []
        for _, r in show.iterrows():
            cover = r["thumb_url"] if isinstance(r["thumb_url"], str) and r["thumb_url"] else ""
            cover_style = f"background-image:url('{html.escape(cover)}')" if cover else ""
            cover_inner = "" if cover else "no cover"
            href = r["discogs_uri"] if isinstance(r["discogs_uri"], str) and r["discogs_uri"] else "#"
            ratio = f"{r['ratio']:.0f}x" if pd.notna(r["ratio"]) else ""
            title = html.escape(str(r["release_title"] or "Untitled"))
            artist = html.escape(str(r["artist_name"] or "Unknown"))
            parts = [r["label_pretty"], r["format_name"],
                     int(r["release_year"]) if pd.notna(r["release_year"]) else None]
            sub = html.escape(" · ".join(str(x) for x in parts if x is not None and str(x) != "nan"))
            want_n = int(r["want"]) if pd.notna(r["want"]) else 0
            have_n = int(r["have"]) if pd.notna(r["have"]) else 0
            nums = f"{want_n} want · {have_n} have"
            cards.append(
                f"<a class='card' href='{html.escape(href)}' target='_blank'>"
                f"<div class='badge'>{ratio}</div>"
                f"<div class='cover' style=\"{cover_style}\">{cover_inner}</div>"
                f"<div class='meta'><div class='t'>{title}</div><div class='a'>{artist}</div>"
                f"<div class='s'>{sub}</div><div class='n'>{nums}</div></div></a>"
            )
        st.markdown(f"<div class='wall'>{''.join(cards)}</div>", unsafe_allow_html=True)
        st.caption(f"Showing the top {len(show)} of {len(fdf):,} matching records.")

with tab_top:
    st.subheader("The 15 most-coveted")
    top = fdf.head(15).assign(lbl=lambda d: d["release_title"] + " - " + d["label_pretty"])
    if len(top):
        st.bar_chart(top.set_index("lbl")[["ratio"]].rename(columns={"ratio": "Desire (want/have)"}),
                     horizontal=True, height=460)

with tab_fmt:
    st.subheader("Physical vs digital")
    g = (fdf.groupby("format_class")
            .agg(records=("release_id", "count"), avg_desire=("ratio", "mean")).reset_index())
    cc1, cc2 = st.columns(2)
    cc1.bar_chart(g.set_index("format_class")[["records"]], height=300)
    cc2.bar_chart(g.set_index("format_class")[["avg_desire"]], height=300)
    st.dataframe(g.rename(columns={"format_class": "Format", "records": "Records",
                                   "avg_desire": "Avg desire"}),
                 use_container_width=True, hide_index=True)

with tab_lab:
    st.subheader("Which label is most coveted?")
    g = (fdf.groupby("label_pretty")
            .agg(records=("release_id", "count"), avg_desire=("ratio", "mean")).reset_index())
    st.bar_chart(g.set_index("label_pretty")[["avg_desire"]], height=300)
    st.dataframe(g.rename(columns={"label_pretty": "Label", "records": "Records",
                                   "avg_desire": "Avg desire"}),
                 use_container_width=True, hide_index=True)

with tab_health:
    st.subheader("Pipeline data health")
    st.caption("How complete the data is per label, and when it last loaded - observability.")
    try:
        h = load_health()
        h["source_label"] = h["source_label"].map(LABEL_NAMES).fillna(h["source_label"])
        st.dataframe(h.rename(columns={
            "source_label": "Label", "releases": "Records", "pct_with_year": "% with year",
            "pct_with_demand_data": "% with demand data", "last_loaded": "Last loaded"}),
            use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"Couldn't load health summary: {e}")

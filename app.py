"""
Grail Index - want vs. ownership across four independent labels.

A browsable index of the most-coveted, least-owned records across four independent
labels. Reads LIVE from the DuckDB gold layer (main.fct_release + dims) built by dbt.

Run from the `pipeline` folder:  streamlit run app.py
"""

import os
import html
import altair as alt
import duckdb
import pandas as pd
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "discogs.duckdb")

LABEL_NAMES = {
    "felt": "FELT", "motion_ward": "Motion Ward",
    "year0001": "Year0001", "posh_isolation": "Posh Isolation",
}

st.set_page_config(page_title="Grail Index", page_icon="◖", layout="wide")


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
               round(100.0*count(release_year)/count(*),0) as pct_year,
               round(100.0*count(case when community_have>0 then 1 end)/count(*),0) as pct_demand,
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
      .concept { color:#5b5347; font-size:.92rem; line-height:1.6; max-width:58rem; }
      .stat { color:#1f1b16; font-size:.8rem; letter-spacing:.04em; margin-top:.4rem; }
      .stat b { color:#b1442f; }
      .wall { display:grid; grid-template-columns:repeat(auto-fill, minmax(150px,1fr));
              gap:12px; margin-top:6px; }
      .card { position:relative; text-decoration:none; color:inherit; display:block;
              background:#f6efe1; border:1px solid #d8cdb6; border-radius:3px; overflow:hidden;
              transition:border-color .12s ease, transform .12s ease; }
      .card:hover { border-color:#1f1b16; transform:translateY(-2px); }
      .cover { width:100%; aspect-ratio:1/1; background:#e7dcc6 center/cover no-repeat;
               display:flex; align-items:center; justify-content:center;
               color:#a89c82; font-size:.6rem; text-transform:uppercase; letter-spacing:.12em; }
      .badge { position:absolute; top:7px; left:7px; background:#b1442f; color:#f6efe1;
               font-weight:700; font-size:.7rem; padding:2px 6px; border-radius:2px; letter-spacing:.02em; }
      .meta { padding:8px 9px 10px; }
      .t { font-weight:700; font-size:.78rem; line-height:1.2; margin-bottom:2px; color:#1f1b16;
           overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .a { color:#6b6353; font-size:.72rem; margin-bottom:6px;
           overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .s { color:#8a7f68; font-size:.66rem; letter-spacing:.03em; }
      .n { color:#9a8e72; font-size:.66rem; margin-top:3px; }
      .readout { background:#f6efe1; border:1px solid #d8cdb6; border-radius:3px;
                 padding:14px 16px; font-size:.78rem; line-height:1.9; color:#1f1b16; }
      .readout .dim { color:#8a7f68; }
      .readout .hd { color:#b1442f; letter-spacing:.04em; }
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    df = load_releases()
except Exception as e:
    st.error(f"Couldn't read the warehouse - run `dbt build` first.\n\n{e}")
    st.stop()

df["label_pretty"] = df["source_label"].map(LABEL_NAMES).fillna(df["source_label"])
df["genre_list"] = df["genres"].apply(lambda s: [g.strip() for g in s.split(",") if g.strip()])

st.title("◖ Grail Index")
st.markdown(
    "<div class='concept'>A desire index for four independent labels - "
    "FELT, Motion Ward, Year0001, Posh Isolation. Every record ranked by "
    "<b>desire</b>: how many people want it for each one that owns it. "
    "Higher = rarer, more coveted.</div>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<div class='stat'><b>{len(df):,}</b> releases · <b>4</b> labels · ranked by desire · "
    f"live from the warehouse</div>",
    unsafe_allow_html=True,
)
st.write("")

st.sidebar.header("Filter")
label_opts = sorted(df["label_pretty"].unique())
sel_labels = st.sidebar.multiselect("Label", label_opts, default=label_opts)
class_opts = sorted(df["format_class"].dropna().unique())
sel_class = st.sidebar.multiselect("Format", class_opts, default=class_opts)
all_genres = sorted({g for lst in df["genre_list"] for g in lst})
sel_genres = st.sidebar.multiselect("Genre (any of)", all_genres, default=[])
min_owners = st.sidebar.slider(
    "Min Owners", 0, 50, 3,
    help="Higher = robust grails. Lower = include extreme 1-2-owner rarities.",
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
c1.metric("In View", f"{len(fdf):,}")
c2.metric("Wanting", f"{int(fdf['want'].fillna(0).sum()):,}")
c3.metric("Owning", f"{int(fdf['have'].fillna(0).sum()):,}")
md = fdf["ratio"].median()
c4.metric("Median Desire", f"{md:.1f}x" if pd.notna(md) else "-")
st.divider()

tab_wall, tab_scatter, tab_fmt, tab_lab, tab_health = st.tabs(
    ["The Wall", "Want vs Have", "Physical · Digital", "By Label", "Data Health"]
)

with tab_wall:
    st.caption("Sorted by desire · click any sleeve to open it on Discogs")
    show = fdf.head(90)
    if len(show) == 0:
        st.info("Nothing matches - loosen the filters.")
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
        st.caption(f"Showing top {len(show)} of {len(fdf):,} matching records")

with tab_scatter:
    st.subheader("Want vs Have")
    st.caption("Each dot is a release. Dots above the dashed parity line are wanted more "
               "than owned - the further above, the bigger the grail.")
    sc = fdf[(fdf["have"].fillna(0) > 0) & (fdf["want"].fillna(0) > 0)].copy()
    if len(sc):
        lo = max(1, int(min(sc["have"].min(), sc["want"].min())))
        hi = int(max(sc["have"].max(), sc["want"].max()))
        dots = alt.Chart(sc).mark_circle(size=55, opacity=0.55).encode(
            x=alt.X("have:Q", scale=alt.Scale(type="log"), title="Owners (have)"),
            y=alt.Y("want:Q", scale=alt.Scale(type="log"), title="Wanters (want)"),
            color=alt.Color("format_class:N", title="Format",
                            scale=alt.Scale(scheme="set2")),
            tooltip=[alt.Tooltip("release_title:N", title="Release"),
                     alt.Tooltip("artist_name:N", title="Artist"),
                     alt.Tooltip("label_pretty:N", title="Label"),
                     "want:Q", "have:Q", alt.Tooltip("ratio:Q", title="Desire", format=".1f")],
        )
        parity = alt.Chart(pd.DataFrame({"have": [lo, hi], "want": [lo, hi]})).mark_line(
            strokeDash=[4, 4], color="#8a7f68").encode(x="have:Q", y="want:Q")
        chart = (dots + parity).properties(height=470).configure_view(
            strokeWidth=0).configure(background="transparent").interactive()
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Nothing to plot - loosen the filters.")

with tab_fmt:
    st.subheader("Physical vs Digital")
    st.caption("Pooled desire = total wanters / total owners in the group (robust to outliers). "
               "n = number of records.")
    g = (fdf.groupby("format_class")
            .agg(n=("release_id", "count"), want=("want", "sum"), have=("have", "sum")).reset_index())
    g["pooled_desire"] = (g["want"] / g["have"].replace(0, pd.NA)).round(2)
    cc1, cc2 = st.columns(2)
    cc1.bar_chart(g.set_index("format_class")[["pooled_desire"]], height=300)
    cc2.bar_chart(g.set_index("format_class")[["n"]], height=300)
    st.dataframe(g.rename(columns={"format_class": "Format", "n": "Records (n)",
                                   "pooled_desire": "Pooled Desire", "want": "Total Want",
                                   "have": "Total Have"}),
                 use_container_width=True, hide_index=True)

with tab_lab:
    st.subheader("Most Coveted Label")
    st.caption("Pooled desire = total wanters / total owners (robust to outliers). "
               "n shown because labels are very uneven in size.")
    g = (fdf.groupby("label_pretty")
            .agg(n=("release_id", "count"), want=("want", "sum"), have=("have", "sum")).reset_index())
    g["pooled_desire"] = (g["want"] / g["have"].replace(0, pd.NA)).round(2)
    g = g.sort_values("pooled_desire", ascending=False)
    st.bar_chart(g.set_index("label_pretty")[["pooled_desire"]], height=300)
    st.dataframe(g.rename(columns={"label_pretty": "Label", "n": "Records (n)",
                                   "pooled_desire": "Pooled Desire", "want": "Total Want",
                                   "have": "Total Have"}),
                 use_container_width=True, hide_index=True)

with tab_health:
    st.subheader("Data Health")
    st.caption("Completeness per label and when each last loaded - pipeline observability")
    try:
        h = load_health()
        total = int(h["releases"].sum())
        snap = pd.to_datetime(h["last_loaded"]).max()
        snap_s = snap.strftime("%Y-%m-%d %H:%M UTC") if pd.notna(snap) else "-"
        lines = [f"<span class='hd'>snap {snap_s} · {total:,} rels · {len(h)} labels</span>", ""]
        for _, r in h.iterrows():
            name = LABEL_NAMES.get(r["source_label"], r["source_label"])
            loaded = pd.to_datetime(r["last_loaded"])
            loaded_s = loaded.strftime("%Y-%m-%d") if pd.notna(loaded) else "-"
            lines.append(
                f"{name:<16} {int(r['releases']):>4} rels   "
                f"y {int(r['pct_year'])}%   d {int(r['pct_demand'])}%   "
                f"<span class='dim'>loaded {loaded_s}</span>"
            )
        st.markdown("<div class='readout'>" + "<br>".join(lines) + "</div>", unsafe_allow_html=True)
        st.caption("y = % with a release year · d = % with want/have demand data")
    except Exception as e:
        st.warning(f"Couldn't load health summary: {e}")

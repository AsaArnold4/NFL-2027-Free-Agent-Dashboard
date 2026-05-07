"""
2027 NFL Free Agent Dashboard — VaynerSports demo.

Design notes:
- SumerSports-inspired dense data table
- VaynerSports copper/bronze palette (extracted from logo)
- ESPN headshots loaded lazily by player slug
- Comparable-deal-based projections (no fabricated numbers)
- Team fits computed from teams with expiring 2027 contracts at the same position
"""
import re
import ast
from pathlib import Path

import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────────────
# Paths & config
# ─────────────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

st.set_page_config(
    page_title="2027 NFL Free Agent Tracker",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# VaynerSports palette (from logo image: copper gradient on near-black)
COPPER = "#C68B5C"
COPPER_DARK = "#7B4A2E"
COPPER_LIGHT = "#E0AD80"
INK = "#1A1410"
INK_SOFT = "#2A2018"
PAPER = "#FBF7F2"
MUTED = "#8B7969"


# ─────────────────────────────────────────────────────────────────────
# Custom CSS — SumerSports-style dense table on copper/cream palette
# ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="st-"], .stApp, [data-testid="stAppViewContainer"] {{
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
}}

[data-testid="stAppViewContainer"] {{
    background: {PAPER};
}}

[data-testid="stHeader"] {{ background: transparent; }}

/* Sidebar */
[data-testid="stSidebar"] {{
    background: {INK};
    border-right: 1px solid {COPPER_DARK};
}}
[data-testid="stSidebar"] * {{ color: {PAPER} !important; }}
[data-testid="stSidebar"] label {{ color: {COPPER_LIGHT} !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 0.5px; }}
[data-testid="stSidebar"] .stSelectbox > div > div, [data-testid="stSidebar"] .stMultiSelect > div > div {{
    background: {INK_SOFT} !important;
    border: 1px solid {COPPER_DARK} !important;
    color: {PAPER} !important;
}}
[data-testid="stSidebar"] input {{ color: {PAPER} !important; background: {INK_SOFT} !important; }}

/* Header banner */
.vs-header {{
    background: linear-gradient(90deg, {COPPER} 0%, {COPPER_DARK} 50%, {INK} 100%);
    padding: 26px 32px;
    border-radius: 8px;
    margin-bottom: 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}}
.vs-header h1 {{
    color: {PAPER} !important;
    font-size: 28px !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px;
    margin: 0 !important;
    line-height: 1.1;
}}
.vs-header p {{
    color: {COPPER_LIGHT} !important;
    margin: 4px 0 0 0 !important;
    font-size: 13px;
    letter-spacing: 0.3px;
}}

/* Stat cards */
.stat-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }}
.stat-card {{
    background: white;
    border: 1px solid #E8DCC8;
    border-radius: 6px;
    padding: 14px 18px;
    border-left: 3px solid {COPPER};
}}
.stat-label {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; color: {MUTED}; font-weight: 600; }}
.stat-value {{ font-size: 26px; font-weight: 800; color: {INK}; margin-top: 2px; line-height: 1.1; }}
.stat-sub {{ font-size: 11px; color: {MUTED}; margin-top: 2px; }}

/* Table styling */
.player-table {{
    background: white;
    border-radius: 6px;
    border: 1px solid #E8DCC8;
    overflow: hidden;
}}
.tbl-head {{
    display: grid;
    grid-template-columns: 50px 60px 2.2fr 60px 80px 50px 1.3fr 1.5fr 1.5fr;
    gap: 12px;
    padding: 11px 16px;
    background: {INK};
    color: {COPPER_LIGHT};
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-weight: 700;
}}
.tbl-row {{
    display: grid;
    grid-template-columns: 50px 60px 2.2fr 60px 80px 50px 1.3fr 1.5fr 1.5fr;
    gap: 12px;
    padding: 10px 16px;
    border-bottom: 1px solid #F0E6D6;
    align-items: center;
    font-size: 13px;
    color: {INK};
    background: white;
}}
.tbl-row:hover {{ background: #FCF6EE; }}
.tbl-row.vs-client {{ background: linear-gradient(90deg, rgba(198,139,92,0.08) 0%, transparent 100%); border-left: 3px solid {COPPER}; padding-left: 13px; }}

.rank {{ color: {MUTED}; font-weight: 600; font-size: 12px; }}
.headshot {{ width: 36px; height: 36px; border-radius: 50%; background: #F0E6D6; object-fit: cover; }}
.player-name {{ font-weight: 600; color: {INK}; }}
.player-meta {{ font-size: 11px; color: {MUTED}; margin-top: 1px; }}
.pos-pill {{ display: inline-block; padding: 2px 8px; background: {INK}; color: {PAPER}; border-radius: 3px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; }}
.fa-badge {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 9px; font-weight: 700; letter-spacing: 0.4px; text-transform: uppercase; }}
.fa-UFA {{ background: {COPPER_DARK}; color: white; }}
.fa-Void {{ background: #6B5A48; color: white; }}
.fa-RFA {{ background: #8B7969; color: white; }}
.fa-ERFA {{ background: #B8A088; color: white; }}
.proj-range {{ font-weight: 700; color: {COPPER_DARK}; }}
.proj-meta {{ font-size: 10px; color: {MUTED}; }}
.agency {{ color: {INK}; font-weight: 500; }}
.agency-vs {{ color: {COPPER_DARK}; font-weight: 700; }}
.no-rep {{ color: #C0B099; font-style: italic; font-size: 11px; }}

/* Filter chip row */
.chip-row {{ margin-bottom: 16px; }}
button[kind="secondary"] {{ background: white !important; color: {INK} !important; border: 1px solid #D8C8B0 !important; border-radius: 4px !important; }}
button[kind="primary"] {{ background: {COPPER} !important; color: {PAPER} !important; border: 1px solid {COPPER_DARK} !important; }}

/* Hide Streamlit branding */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
.stDeployButton {{ display: none; }}

/* Player detail drawer */
.detail-section {{ background: white; padding: 18px; border-radius: 6px; border: 1px solid #E8DCC8; margin-bottom: 12px; }}
.detail-h {{ font-size: 11px; text-transform: uppercase; color: {MUTED}; letter-spacing: 0.5px; font-weight: 700; margin-bottom: 8px; }}
.comp-item {{ padding: 6px 10px; background: #FCF6EE; border-left: 2px solid {COPPER}; margin-bottom: 4px; font-size: 12px; }}
.fit-item {{ padding: 8px 12px; background: #FCF6EE; border-radius: 4px; margin-bottom: 6px; font-size: 12px; }}
.fit-team {{ font-weight: 700; color: {COPPER_DARK}; }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    fa = pd.read_csv(DATA_DIR / "fa_2027_clean.csv")
    proj = pd.read_csv(DATA_DIR / "fa_2027_projected.csv")
    reps = pd.read_csv(DATA_DIR / "athleteagent_reps.csv")

    # Merge projections (projected file already has all FA cols + projection cols)
    df = proj.copy()

    # Merge reps via slug
    reps_slim = reps[["slug", "agency_name", "agency_id"]].drop_duplicates(subset="slug")
    df = df.merge(reps_slim, on="slug", how="left")

    # Mark VaynerSports clients
    df["is_vs"] = df["agency_name"].fillna("") == "VaynerSports"

    return df


df = load_data()

ALL_TEAMS = sorted(df["team"].dropna().unique().tolist())
ALL_POS = sorted(df["pos_group"].dropna().unique().tolist())
ALL_AGENCIES = sorted(df["agency_name"].dropna().unique().tolist())


# ─────────────────────────────────────────────────────────────────────
# Sidebar filters
# ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:18px;'>"
                f"<div style='width:32px;height:32px;background:{COPPER};border-radius:4px;display:flex;align-items:center;justify-content:center;font-weight:800;color:{INK};font-size:14px;'>VS</div>"
                f"<div style='font-weight:800;font-size:15px;'>2027 FA TRACKER</div></div>",
                unsafe_allow_html=True)

    st.markdown(f"<div style='font-size:11px;color:{COPPER_LIGHT};margin-bottom:14px;'>Built for the VaynerSports apprenticeship interview</div>", unsafe_allow_html=True)

    st.divider()

    st.markdown("**Search**")
    search = st.text_input("Search", placeholder="Player, team, agent...", label_visibility="collapsed")

    st.markdown("**Position**")
    pos_filter = st.multiselect("Position", ALL_POS, default=[], label_visibility="collapsed")

    st.markdown("**Team**")
    team_filter = st.multiselect("Team", ALL_TEAMS, default=[], label_visibility="collapsed")

    st.markdown("**Agency**")
    agency_filter = st.multiselect("Agency", ALL_AGENCIES, default=[], label_visibility="collapsed")

    st.markdown("**FA Type**")
    fa_types = ["UFA", "Void", "RFA", "ERFA"]
    fa_filter = st.multiselect("FA Type", fa_types, default=["UFA", "Void"], label_visibility="collapsed")

    st.markdown("**Min. Prior APY ($M)**")
    min_apy = st.slider("Min APY", 0, 50, 1, label_visibility="collapsed") * 1_000_000

    vs_only = st.checkbox("Show VaynerSports clients only", value=False)

    st.divider()
    st.caption(f"**Sources**: OverTheCap (free agent list, contracts), AthleteAgent.com (representation), curated comps from active NFL contracts.")


# ─────────────────────────────────────────────────────────────────────
# Apply filters
# ─────────────────────────────────────────────────────────────────────
filtered = df.copy()

if search:
    s = search.lower()
    mask = (
        filtered["name"].str.lower().str.contains(s, na=False)
        | filtered["team"].str.lower().str.contains(s, na=False)
        | filtered["agency_name"].fillna("").str.lower().str.contains(s, na=False)
    )
    filtered = filtered[mask]

if pos_filter:
    filtered = filtered[filtered["pos_group"].isin(pos_filter)]
if team_filter:
    filtered = filtered[filtered["team"].isin(team_filter)]
if agency_filter:
    filtered = filtered[filtered["agency_name"].isin(agency_filter)]
if fa_filter:
    filtered = filtered[filtered["fa_type"].isin(fa_filter)]
if min_apy:
    filtered = filtered[filtered["prior_apy"] >= min_apy]
if vs_only:
    filtered = filtered[filtered["is_vs"]]

filtered = filtered.sort_values("prior_apy", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class='vs-header'>
    <h1>2027 NFL Free Agent Tracker</h1>
    <p>Live valuation, representation, and team-fit context for every upcoming free agent</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# Stat cards
# ─────────────────────────────────────────────────────────────────────
total_count = len(filtered)
vs_count = int(filtered["is_vs"].sum())
top_apy = filtered["prior_apy"].max() / 1e6 if total_count else 0
top_player = filtered.iloc[0]["name"] if total_count else "—"
agency_count = filtered["agency_name"].dropna().nunique()

st.markdown(f"""
<div class='stat-row'>
    <div class='stat-card'><div class='stat-label'>Free Agents</div><div class='stat-value'>{total_count}</div><div class='stat-sub'>matching filters</div></div>
    <div class='stat-card'><div class='stat-label'>Top Prior APY</div><div class='stat-value'>${top_apy:.0f}M</div><div class='stat-sub'>{top_player}</div></div>
    <div class='stat-card'><div class='stat-label'>VaynerSports Clients</div><div class='stat-value'>{vs_count}</div><div class='stat-sub'>in current view</div></div>
    <div class='stat-card'><div class='stat-label'>Agencies Repped</div><div class='stat-value'>{agency_count}</div><div class='stat-sub'>verified via AthleteAgent</div></div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# Helper: ESPN headshot URL by name (best-effort)
# ─────────────────────────────────────────────────────────────────────
@st.cache_data
def load_espn_id_map():
    p = DATA_DIR / "espn_ids.csv"
    if not p.exists():
        return {}
    m = pd.read_csv(p)
    return dict(zip(m["slug"], m["espn_id"]))


ESPN_IDS = load_espn_id_map()


def headshot_url(slug: str) -> str:
    eid = ESPN_IDS.get(slug)
    if eid:
        return f"https://a.espncdn.com/i/headshots/nfl/players/full/{eid}.png"
    # Generic fallback (silhouette)
    return "https://a.espncdn.com/i/teamlogos/leagues/500/nfl.png"


# ─────────────────────────────────────────────────────────────────────
# Main table — render rows manually for full design control
# ─────────────────────────────────────────────────────────────────────
PAGE_SIZE = 50
total = len(filtered)

if total == 0:
    st.info("No players match the current filters. Adjust filters in the sidebar.")
else:
    # Pagination
    page = st.session_state.get("page", 1)
    max_page = (total - 1) // PAGE_SIZE + 1

    cols = st.columns([1, 1, 8, 1, 1])
    with cols[0]:
        if st.button("← Prev", disabled=(page <= 1)):
            st.session_state["page"] = page - 1
            st.rerun()
    with cols[2]:
        st.markdown(f"<div style='text-align:center;color:{MUTED};font-size:13px;padding-top:6px;'>Showing {(page-1)*PAGE_SIZE + 1}–{min(page*PAGE_SIZE, total)} of {total}</div>", unsafe_allow_html=True)
    with cols[4]:
        if st.button("Next →", disabled=(page >= max_page)):
            st.session_state["page"] = page + 1
            st.rerun()

    page_df = filtered.iloc[(page-1)*PAGE_SIZE : page*PAGE_SIZE]

    # Header row
    st.markdown("""
    <div class='player-table'>
      <div class='tbl-head'>
        <span>#</span>
        <span></span>
        <span>Player</span>
        <span>Pos</span>
        <span>Team</span>
        <span>Age</span>
        <span>Prior APY</span>
        <span>2027 Projection</span>
        <span>Representation</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    for i, (_, row) in enumerate(page_df.iterrows(), start=(page-1)*PAGE_SIZE + 1):
        name = row["name"]
        pos = row["pos_group"]
        team = row["team"]
        age = int(row["age"]) if pd.notna(row["age"]) else "—"
        fa_type = row["fa_type"]
        apy_m = row["prior_apy"] / 1e6 if pd.notna(row["prior_apy"]) else 0
        low = row.get("low")
        high = row.get("high")
        comp_count = int(row.get("comp_count", 0)) if pd.notna(row.get("comp_count")) else 0
        agency = row.get("agency_name")
        is_vs = row.get("is_vs", False)
        slug = row.get("slug", "")

        if pd.notna(low) and pd.notna(high):
            proj_str = f"${low:.0f}–${high:.0f}M"
            proj_meta = f"{comp_count} comps"
        else:
            proj_str = "—"
            proj_meta = "insufficient data"

        if agency and pd.notna(agency):
            agency_html = f"<span class='{'agency-vs' if is_vs else 'agency'}'>{agency}</span>"
        else:
            agency_html = "<span class='no-rep'>not in AthleteAgent</span>"

        row_class = "tbl-row vs-client" if is_vs else "tbl-row"

        headshot = headshot_url(slug)

        st.markdown(f"""
        <div class='{row_class}'>
          <span class='rank'>#{i}</span>
          <img class='headshot' src='{headshot}' onerror="this.style.display='none'"/>
          <div>
            <div class='player-name'>{name}{' 🟫' if is_vs else ''}</div>
            <div class='player-meta'><span class='fa-badge fa-{fa_type}'>{fa_type}</span></div>
          </div>
          <span class='pos-pill'>{pos}</span>
          <span style='font-weight:600;color:{INK};'>{team}</span>
          <span style='color:{MUTED};'>{age}</span>
          <span style='font-weight:700;color:{INK};'>${apy_m:.1f}M</span>
          <div>
            <div class='proj-range'>{proj_str}</div>
            <div class='proj-meta'>{proj_meta}</div>
          </div>
          <div>{agency_html}</div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# Player detail drawer (expandable section)
# ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🔍 Player Deep Dive")

if total > 0:
    player_options = filtered["name"].tolist()
    selected_name = st.selectbox("Select a player for detailed projections, comps, and team fits", player_options, label_visibility="collapsed")

    p = filtered[filtered["name"] == selected_name].iloc[0]

    col_a, col_b = st.columns([1, 2])

    with col_a:
        slug = p.get("slug", "")
        st.markdown(f"<img src='{headshot_url(slug)}' style='width:140px;height:140px;border-radius:10px;background:#F0E6D6;object-fit:cover;border:3px solid {COPPER};'/>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:22px;font-weight:800;color:{INK};margin-top:10px;'>{p['name']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:13px;color:{MUTED};margin-bottom:10px;'>{p['pos_group']} · {p['team']} · Age {int(p['age']) if pd.notna(p['age']) else '?'} · {p['fa_type']}</div>", unsafe_allow_html=True)

        if p["is_vs"]:
            st.markdown(f"<div style='background:{COPPER};color:{INK};padding:6px 12px;border-radius:4px;font-weight:700;font-size:12px;display:inline-block;'>VAYNERSPORTS CLIENT</div>", unsafe_allow_html=True)
        elif pd.notna(p.get("agency_name")):
            st.markdown(f"<div style='background:{INK};color:{COPPER_LIGHT};padding:6px 12px;border-radius:4px;font-size:12px;display:inline-block;'>Repped by {p['agency_name']}</div>", unsafe_allow_html=True)

    with col_b:
        # Projection section
        if pd.notna(p.get("low")) and pd.notna(p.get("high")):
            st.markdown(f"""
            <div class='detail-section'>
              <div class='detail-h'>2027 Projection</div>
              <div style='font-size:32px;font-weight:800;color:{COPPER_DARK};line-height:1;'>${p['low']:.0f}M – ${p['high']:.0f}M</div>
              <div style='font-size:12px;color:{MUTED};margin-top:6px;'>{p.get('method', '')}</div>
            </div>
            """, unsafe_allow_html=True)

            # Comparable contracts
            comp_str = p.get("comp_names", "[]")
            try:
                comps = ast.literal_eval(comp_str) if isinstance(comp_str, str) else comp_str
            except (ValueError, SyntaxError):
                comps = []

            if comps:
                comp_html = "<div class='detail-section'><div class='detail-h'>Comparable Contracts</div>"
                for c in comps[:4]:
                    comp_html += f"<div class='comp-item'>{c}</div>"
                comp_html += "</div>"
                st.markdown(comp_html, unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='detail-section'><div class='detail-h'>Projection</div><div style='color:{MUTED};font-size:13px;'>Insufficient comparable contracts to project a defensible range.</div></div>", unsafe_allow_html=True)

        # Team fits
        # Find teams with another 2027 FA at the same position (signaling positional need)
        same_pos_fas = df[(df["pos_group"] == p["pos_group"]) & (df["name"] != p["name"])]
        teams_with_need = same_pos_fas.groupby("team")["prior_apy"].agg(["max", "count"]).reset_index()
        teams_with_need = teams_with_need.sort_values("max", ascending=False).head(5)

        if len(teams_with_need):
            fits_html = "<div class='detail-section'><div class='detail-h'>Potential Team Fits</div>"
            fits_html += f"<div style='font-size:11px;color:{MUTED};margin-bottom:8px;'>Teams with expiring contracts at {p['pos_group']} (highest-paid current incumbent):</div>"
            for _, t in teams_with_need.iterrows():
                fits_html += f"<div class='fit-item'><span class='fit-team'>{t['team']}</span> — incumbent at ${t['max']/1e6:.1f}M APY · {t['count']} expiring {p['pos_group']}s</div>"
            fits_html += "</div>"
            st.markdown(fits_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# Footer / methodology
# ─────────────────────────────────────────────────────────────────────
st.markdown("---")

with st.expander("📊 Methodology & data sources"):
    st.markdown("""
**Free agent list & contract data**: OverTheCap.com 2027 free agency tracker (876 meaningful FAs after filtering ERFA depth players).

**Representation data**: AthleteAgent.com agency-clients pages. The per-player representation pages are paywalled, but agency-level client lists are public — we invert by scraping each agency's roster to build the player→agency lookup. To refresh, run `python scripts/scrape_athleteagent.py --refresh-index`.

**2027 projections**: Range-based, derived from comparable active NFL contracts at the same position group (±3 years of age). The projection shows the 25th–75th percentile of comparable APYs, scaled modestly by snap share. We deliberately do NOT generate single-point projections — every range is grounded in named, real contracts which are surfaced in the detail view.

**Team fits**: Teams ranked by (a) presence of expiring contracts at the same position in 2027 (signaling positional need), and (b) APY of incumbent (signaling willingness to spend at the position).

**What's deliberately omitted**:
- We don't fabricate agent names when AthleteAgent has no entry — those rows show "not in AthleteAgent" rather than guessing.
- We don't generate single-number market projections — agents bring scouting context that anchors a final number.
- We don't include rookie ERFA players with <30% snap share (no agent leverage, not relevant to FA conversations).
""")

st.markdown(f"<div style='text-align:center;font-size:11px;color:{MUTED};margin-top:20px;'>2027 NFL Free Agent Tracker · Built for VaynerSports · {len(df)} players tracked</div>", unsafe_allow_html=True)

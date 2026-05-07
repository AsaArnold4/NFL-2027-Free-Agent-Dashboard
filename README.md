# 2027 NFL Free Agent Tracker

A dashboard for free-agent prep, built for the VaynerSports apprenticeship interview.

Live valuation, representation, and team-fit context for every meaningful upcoming 2027 NFL free agent (876 players).

## What it does

- Lists every 2027 NFL free agent with prior contract data, age, and snap share
- Identifies which agency represents each player (verified from public sources, not fabricated)
- Projects 2027 contract value as a **range** grounded in named comparable contracts (no AI-generated single-point projections)
- Suggests team fits based on which teams have expiring contracts at the same position
- Flags VaynerSports clients prominently throughout the UI

## Quick start (local)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501

## Deploy to Streamlit Cloud (5 min, free, gets you a public link)

1. Create a new public GitHub repo, e.g. `nfl-fa-2027`
2. Upload all files in this folder to the repo (drag-and-drop in GitHub web UI works fine)
3. Go to https://share.streamlit.io and sign in with GitHub
4. Click **New app** → select your repo, branch `main`, main file `app.py`
5. Click **Deploy** — wait ~2 minutes
6. You'll get a public URL like `https://nfl-fa-2027.streamlit.app` — share with the interviewer

## Data architecture

```
data/
├── fa_2027_raw.csv            # OTC export, untouched (1409 rows)
├── fa_2027_clean.csv          # Cleaned + filtered to meaningful FAs (876 rows)
├── fa_2027_projected.csv      # With AAV projection ranges + comp names
├── athleteagent_reps.csv      # player → agency lookup (verified)
├── comps_seed.csv             # Active NFL star contracts to anchor projections
└── espn_ids.csv               # Player slug → ESPN headshot ID
```

## Refreshing the data

The app reads pre-built CSVs at runtime — no scraping during user requests. To refresh:

```bash
# 1. Re-clean the OTC CSV (after replacing fa_2027_raw.csv with a fresh export)
python scripts/clean_fa_csv.py

# 2. Re-scrape AthleteAgent for agent data
python scripts/scrape_athleteagent.py --refresh-index

# 3. Build / refresh ESPN headshot IDs
python scripts/build_espn_ids.py

# 4. Recompute projections
python scripts/project_value.py
```

The scrapers use real user-agent headers and polite rate-limiting (~0.6s between requests). They run cleanly on a normal machine and on Streamlit Cloud.

## Methodology

### Free agent list
OverTheCap's free agency tracker exports a CSV of every player whose contract expires by year. We filter to:
- UFA, Void, RFA tier (true free agents)
- ERFA only if snap share ≥ 30% (filters out practice squad / deep depth)
- Drops ERFA players under $1M APY who played <30% snaps

This produces 876 meaningful 2027 FAs from 1409 raw rows.

### Representation data
AthleteAgent.com's per-player representation pages are paywalled. The agency-level **client lists** are public. We invert: scrape each NFL agency's `/agencies/{id}/clients` page and build a player→agency lookup. VaynerSports (agency_id=322) is verified from this approach.

When a player is not in AthleteAgent's database, the row shows "not in AthleteAgent" rather than a fabricated agent name.

### 2027 projections
Range-based, never single-point. For each FA, we:
1. Find comparable players at the same position group within ±3 years of age
2. Pull their current APYs from a seed of active NFL star contracts + the FA pool
3. Show the 25th–75th percentile range
4. Adjust modestly by snap share (capped at ±20%)
5. Surface the 4 closest comparables in the player detail view

The agent gets a defensible range and the named comparables behind it. They bring scouting judgment to land on a final number — this tool doesn't pretend to do that.

### Team fits
For each FA, we surface 5 teams ranked by:
- Number of expiring contracts at the same position in 2027 (signal: positional need)
- APY of the highest-paid current incumbent (signal: willingness to spend)

This is intentionally simple. A more sophisticated v2 would layer in 2027 cap space projections and scheme tags.

## Design choices

- **Color palette**: Copper/bronze gradient sampled from VaynerSports' brand image, on a cream background
- **Layout**: SumerSports-inspired dense data table with rank, headshot, and key stats inline
- **Filters**: Sidebar multi-select (position, team, agency, FA type) + dedicated VaynerSports toggle
- **Detail view**: Click any player in the dropdown for full projection, comps, and fits

## Trade-offs and what's next

**Honest limits:**
- AthleteAgent's coverage is incomplete — many players have no entry. The more agencies we scrape, the better coverage gets. Currently the bundled CSV has ~57 VaynerSports clients hand-pulled; a full run of `scrape_athleteagent.py` against the agency index will add hundreds more.
- Comp pool is anchored on a hand-curated `comps_seed.csv` of ~80 active star contracts. A v2 would scrape OTC's full position pages for a richer comp set.
- Team-fit logic doesn't yet use 2027 cap space projections — this is the highest-value v2 add.
- Some players have insufficient comps for a projection (rare positions, edge ages); we surface "—" rather than guess.

**What I'd build next (in priority order):**
1. Full agency scrape (one `python scripts/scrape_athleteagent.py` call, populates the rep data for all 876 FAs)
2. 2027 cap space integration in team fits
3. Stat overlay (recent season EPA, success rate, snap share trend) per player
4. Side-by-side player comparison
5. CSV export filtered to current view

## File tree

```
nfl_fa_app/
├── app.py                          # Streamlit dashboard
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── data/
│   ├── fa_2027_raw.csv             # OTC export (input)
│   ├── fa_2027_clean.csv           # Filtered FAs
│   ├── fa_2027_projected.csv       # FAs + projection columns
│   ├── athleteagent_reps.csv       # Player → agency map
│   ├── comps_seed.csv              # Active NFL star contracts
│   └── espn_ids.csv                # Player slug → ESPN ID (built by script)
└── scripts/
    ├── clean_fa_csv.py             # OTC CSV → clean dataset
    ├── scrape_athleteagent.py      # Build agent representation CSV
    ├── project_value.py            # Compute projection ranges
    └── build_espn_ids.py           # Pull ESPN headshot IDs
```

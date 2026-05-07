"""
Build a player_slug → ESPN_id mapping for headshot URLs.

ESPN's roster API is free and key-less:
  https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team}/roster

We hit each team's roster, grab every athlete's id, and slugify their name.

Usage:
    python scripts/build_espn_ids.py

Output:
    data/espn_ids.csv  (slug, espn_id)

Run this once locally then commit. The Streamlit app reads the CSV at startup.
"""
import re
import csv
import time
import requests
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ESPN_TEAMS = [
    "ARI","ATL","BAL","BUF","CAR","CHI","CIN","CLE","DAL","DEN",
    "DET","GB","HOU","IND","JAX","KC","LV","LAC","LAR","MIA",
    "MIN","NE","NO","NYG","NYJ","PHI","PIT","SF","SEA","TB",
    "TEN","WSH",
]

ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team}/roster"


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^\w\s'-]", "", s)
    s = s.replace("'", "").replace(".", "")
    s = re.sub(r"\s+", "-", s.strip())
    return s


def fetch_team(team: str) -> list[dict]:
    url = ROSTER_URL.format(team=team)
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"[{team}] FAIL: {e}")
        return []
    data = r.json()
    rows = []
    for grp in data.get("athletes", []):
        for a in grp.get("items", []):
            name = a.get("displayName") or a.get("fullName") or ""
            espn_id = a.get("id") or a.get("uid")
            if name and espn_id:
                rows.append({"slug": slugify(name), "espn_id": str(espn_id), "name": name, "team": team})
    return rows


def main():
    DATA_DIR.mkdir(exist_ok=True)
    all_rows = []
    for t in ESPN_TEAMS:
        rows = fetch_team(t)
        print(f"[{t}] {len(rows)} players")
        all_rows.extend(rows)
        time.sleep(0.3)

    # Dedupe by slug, keeping first occurrence
    seen = set()
    deduped = []
    for r in all_rows:
        if r["slug"] not in seen:
            seen.add(r["slug"])
            deduped.append(r)

    out = DATA_DIR / "espn_ids.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["slug", "espn_id", "name", "team"])
        w.writeheader()
        w.writerows(deduped)
    print(f"\n[done] {len(deduped)} unique players → {out}")


if __name__ == "__main__":
    main()

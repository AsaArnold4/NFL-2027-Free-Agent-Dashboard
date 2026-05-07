"""
Scrape AthleteAgent.com agency-clients pages to build a player→agent/agency lookup.

Why this approach:
- AthleteAgent's per-player /representation page is paywalled (returns "Dummy Agency")
- The /agencies/{id}/clients page is FREE and lists every client publicly
- We invert: scrape every NFL agency's client list, build name→agency map

Usage:
    python scripts/scrape_athleteagent.py             # scrapes top NFL agencies
    python scripts/scrape_athleteagent.py --agencies  # refreshes agency index too

Output:
    data/athleteagent_index.csv   - agency_id, agency_name
    data/athleteagent_reps.csv    - player_name, slug, agency_name, agency_id, league, aav

This script is meant to run once locally then commit the CSVs.
On Streamlit Cloud the app reads the prebuilt CSVs (no scraping at runtime).
"""
import re
import csv
import time
import argparse
import requests
from pathlib import Path
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INDEX_URL = "https://www.athleteagent.com/agencies"
CLIENTS_URL = "https://www.athleteagent.com/agencies/{id}/clients"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
}

# Hand-curated list of major NFL-relevant agencies (AthleteAgent agency IDs).
# VaynerSports = 322 (verified from earlier fetch).
# Others discovered by browsing /agencies. Edit/extend as needed.
NFL_AGENCY_IDS = {
    322:  "VaynerSports",
    347:  "ACES",
    # Lookup the rest at runtime by scraping /agencies index
}


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^\w\s'-]", "", s)
    s = s.replace("'", "").replace(".", "")
    s = re.sub(r"\s+", "-", s.strip())
    return s


def scrape_agency_index() -> dict[int, str]:
    """
    Scrape the full agencies index. Returns {agency_id: agency_name}.
    """
    print(f"[index] GET {INDEX_URL}")
    r = requests.get(INDEX_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    out = {}
    for a in soup.select("a[href*='/agencies/']"):
        m = re.search(r"/agencies/(\d+)/clients", a.get("href", ""))
        if m:
            agency_id = int(m.group(1))
            name = a.get_text(strip=True)
            if name:
                out[agency_id] = name
    print(f"[index] Found {len(out)} agencies")
    return out


def scrape_agency_clients(agency_id: int, agency_name: str) -> list[dict]:
    """
    Scrape one agency's clients page. Returns list of client dicts.
    """
    url = CLIENTS_URL.format(id=agency_id)
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"[agency {agency_id}] FAIL: {e}")
        return []

    soup = BeautifulSoup(r.text, "lxml")
    clients = []
    # Tables on these pages have columns: NAME | SPORT | LEAGUE | AVG ANNUAL PAY
    for tr in soup.select("table tr"):
        cells = tr.find_all("td")
        if len(cells) < 3:
            continue
        link = cells[0].find("a")
        if not link:
            continue
        name = link.get_text(strip=True)
        sport = cells[1].get_text(strip=True) if len(cells) > 1 else ""
        league = cells[2].get_text(strip=True) if len(cells) > 2 else ""
        aav_raw = cells[3].get_text(strip=True) if len(cells) > 3 else ""
        # Only keep NFL clients
        if league != "NFL":
            continue
        try:
            aav = float(aav_raw.replace("$", "").replace(",", "")) if aav_raw else 0.0
        except ValueError:
            aav = 0.0
        clients.append({
            "name": name,
            "slug": slugify(name),
            "agency_id": agency_id,
            "agency_name": agency_name,
            "league": league,
            "aav_aa": aav,
        })
    return clients


def is_likely_nfl_agency(name: str) -> bool:
    """Heuristic: skip clearly-not-NFL agencies to limit traffic."""
    name_l = name.lower()
    skip_keywords = [
        "cricket", "fútbol", "futbol", " soccer", "ipl", "tennis", "golf",
        "hockey", "esports", "gaming", "korea", "japan", "brasil", "brazil",
        "argentina", "mexico", "colombia", "chile", "pharoahs", "f1 ",
    ]
    return not any(kw in name_l for kw in skip_keywords)


def main(refresh_index: bool, max_agencies: int | None):
    DATA_DIR.mkdir(exist_ok=True)
    index_csv = DATA_DIR / "athleteagent_index.csv"
    reps_csv = DATA_DIR / "athleteagent_reps.csv"

    # Step 1: agency index
    if refresh_index or not index_csv.exists():
        idx = scrape_agency_index()
        with index_csv.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["agency_id", "agency_name"])
            for aid, aname in sorted(idx.items()):
                w.writerow([aid, aname])
        print(f"[index] Saved → {index_csv}")
    else:
        idx = {}
        with index_csv.open() as f:
            r = csv.DictReader(f)
            for row in r:
                idx[int(row["agency_id"])] = row["agency_name"]
        print(f"[index] Loaded {len(idx)} agencies from cache")

    # Step 2: scrape each agency's NFL clients
    candidates = [(aid, name) for aid, name in idx.items() if is_likely_nfl_agency(name)]
    if max_agencies:
        candidates = candidates[:max_agencies]
    print(f"[scrape] Will hit {len(candidates)} agencies")

    all_reps = []
    for i, (aid, aname) in enumerate(candidates, 1):
        clients = scrape_agency_clients(aid, aname)
        if clients:
            print(f"[{i}/{len(candidates)}] {aname} (id={aid}): {len(clients)} NFL clients")
            all_reps.extend(clients)
        time.sleep(0.6)  # be polite

    with reps_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "slug", "agency_id", "agency_name", "league", "aav_aa"])
        w.writeheader()
        w.writerows(all_reps)
    print(f"\n[done] {len(all_reps)} NFL player-agency rows → {reps_csv}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--refresh-index", action="store_true", help="Re-scrape agencies index")
    p.add_argument("--max", type=int, default=None, help="Max agencies to scrape (debug)")
    args = p.parse_args()
    main(args.refresh_index, args.max)

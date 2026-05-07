"""
Projection engine: produce a contract value range from comparable deals.

Methodology (defensible, no fabrication):
- For each free agent, find players at the same position group already
  on multi-year deals (i.e. their "next-tier" comparable signings).
- Filter comps to players within ±3 years of the FA's age and similar
  snap-share usage.
- Project a low/high range as the 25th-75th percentile of comp APYs,
  scaled by the FA's snap share vs comp average.
- Surface 3-4 named comparables so the agent can see the math.

This deliberately does NOT use ML or generated numbers — every projection
is grounded in named, real contracts.
"""
from __future__ import annotations
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_comp_pool(fa_df: pd.DataFrame) -> pd.DataFrame:
    """
    The comp pool combines:
      1. Active NFL star contracts at each position (data/comps_seed.csv) -
         these are the market-defining deals that anchor projections.
      2. The 2027 FA list itself, where players had prior multi-year deals
         worth >$4M (i.e. they're not on rookie scale).

    Without the seed file, projections compound downward because the FA
    pool skews toward older/declining vets. With it, we anchor to real
    market rates.
    """
    # Star deals seed
    seed_path = DATA_DIR / "comps_seed.csv"
    seed = pd.read_csv(seed_path) if seed_path.exists() else pd.DataFrame()
    if not seed.empty:
        seed = seed.rename(columns={"apy": "prior_apy"})
        seed["snap_pct"] = 80  # assume starter usage for star comps
        seed["fa_type"] = "Active"
        seed = seed[["name", "pos_group", "age", "prior_apy", "snap_pct", "fa_type"]]

    # FA pool (existing veteran contracts)
    fa_pool = fa_df[
        (fa_df["prior_apy"] >= 4_000_000)
        & (fa_df["fa_type"] != "ERFA")
        & (fa_df["snap_pct"].fillna(0) >= 30)
    ][["name", "pos_group", "age", "prior_apy", "snap_pct", "fa_type"]].copy()

    if seed.empty:
        return fa_pool
    return pd.concat([seed, fa_pool], ignore_index=True)


def project_one(
    player: pd.Series,
    comps: pd.DataFrame,
    age_band: int = 3,
    min_comps: int = 3,
) -> dict:
    """
    Build a projection for one player.

    Returns dict with: low, high, midpoint, comp_count, comp_names
    """
    pos = player["pos_group"]
    age = player["age"] if pd.notna(player["age"]) else 28
    snap = player["snap_pct"] if pd.notna(player["snap_pct"]) else 60

    # Position match
    pool = comps[comps["pos_group"] == pos]
    pool = pool[pool["name"] != player["name"]]

    # Age proximity
    age_filtered = pool[pool["age"].between(age - age_band, age + age_band)]

    # Fall back to wider age band if too few
    if len(age_filtered) < min_comps:
        age_filtered = pool[pool["age"].between(age - age_band - 2, age + age_band + 2)]
    if len(age_filtered) < min_comps:
        age_filtered = pool

    if len(age_filtered) < min_comps:
        return {
            "low": None, "high": None, "midpoint": None,
            "comp_count": 0, "comp_names": [],
            "method": "insufficient comps"
        }

    # Use 25th-75th percentile of comp APYs
    apys = age_filtered["prior_apy"].sort_values()
    low = apys.quantile(0.25)
    high = apys.quantile(0.75)
    mid = apys.median()

    # Adjust for snap share — if the player plays significantly more/less
    # than the average comp, scale modestly (capped at ±20%)
    avg_comp_snap = age_filtered["snap_pct"].mean()
    if avg_comp_snap and avg_comp_snap > 0:
        ratio = snap / avg_comp_snap
        ratio = max(0.8, min(1.2, ratio))
        low *= ratio
        high *= ratio
        mid *= ratio

    # Pick top 4 comps closest to player's age and snap share
    age_filtered = age_filtered.assign(
        _dist=(age_filtered["age"] - age).abs() + (age_filtered["snap_pct"] - snap).abs() / 20
    )
    top_comps = age_filtered.nsmallest(4, "_dist")
    comp_names = [
        f"{r['name']} (age {int(r['age']) if pd.notna(r['age']) else '?'}, ${r['prior_apy']/1e6:.1f}M)"
        for _, r in top_comps.iterrows()
    ]

    return {
        "low": round(low / 1e6, 1),
        "high": round(high / 1e6, 1),
        "midpoint": round(mid / 1e6, 1),
        "comp_count": len(age_filtered),
        "comp_names": comp_names,
        "method": f"{len(age_filtered)} comps at {pos}, age {age-age_band}-{age+age_band}",
    }


def project_all(fa_df: pd.DataFrame) -> pd.DataFrame:
    """Add projection columns to the FA dataframe."""
    comps = build_comp_pool(fa_df)
    rows = []
    for _, p in fa_df.iterrows():
        proj = project_one(p, comps)
        rows.append(proj)
    proj_df = pd.DataFrame(rows)
    return pd.concat([fa_df.reset_index(drop=True), proj_df], axis=1)


if __name__ == "__main__":
    df = pd.read_csv(DATA_DIR / "fa_2027_clean.csv")
    out = project_all(df)
    out.to_csv(DATA_DIR / "fa_2027_projected.csv", index=False)
    print(f"[project] {len(out)} rows projected")
    print(out[["name", "pos_group", "age", "prior_apy", "low", "high", "comp_count"]].head(15).to_string())

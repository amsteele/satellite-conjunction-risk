import numpy as np
import pandas as pd
from typing import Optional
from scipy.spatial import cKDTree

"""
    Detect close approaches using altitude binning + KD-tree.

    Required traj_df columns:
      ['time_utc','satnum','x_km','y_km','z_km','alt_km','sgp4_err']

    If out_parquet_path is provided, writes results to part files and returns empty df.
"""

def _pairs_cross_within_threshold(posA: np.ndarray, posB: np.ndarray, r: float):
    # return index pairs (i,j) with i in A and j in B that are within radius r.
    # uses KDTree query_ball_tree.

    treeA = cKDTree(posA)
    treeB = cKDTree(posB)
    neighbors = treeA.query_ball_tree(treeB, r=r)  # list-of-lists
    pairs = []
    for i, js in enumerate(neighbors):
        for j in js:
            pairs.append((i, j))
    return np.asarray(pairs, dtype=int)

def detect_close_approaches_kdtree(
    traj_df: pd.DataFrame,
    *,
    threshold_km: float,
    alt_bin_km: float,
    leobound_km: float,
    require_sgp4_ok: bool = True,
    out_parquet_path: Optional[str] = None,
    flush_every: int = 50,
) -> pd.DataFrame:

    required = {"time_utc", "satnum", "x_km", "y_km", "z_km", "alt_km", "sgp4_err"}
    missing = required - set(traj_df.columns)
    if missing:
        raise ValueError(f"traj_df missing columns: {missing}")

    df = traj_df.copy()
    df = df.dropna(subset=["time_utc", "satnum", "x_km", "y_km", "z_km", "alt_km"])
    df["satnum"] = df["satnum"].astype(int)

    if require_sgp4_ok:
        df = df[df["sgp4_err"] == 0]

    # focus on LEO
    df = df[df["alt_km"] <= leobound_km]

    # altitude bin for pruning
    df["alt_bin"] = (np.floor(df["alt_km"] / alt_bin_km) * alt_bin_km).astype(int)

    events_buffer = []
    timesteps_processed = 0

    for t, gt in df.groupby("time_utc", sort=True):
        timesteps_processed += 1

        # build dict of altitude bins for this timestep
        bins = {b: gb for b, gb in gt.groupby("alt_bin", sort=False)}

        # compare within-bin, and bin to adjacent bin (b + alt_bin_km)
        for b in sorted(bins.keys()):
            gb = bins[b].drop_duplicates(subset=["satnum"], keep="first")
            if len(gb) < 2:
                continue

            sats_b = gb["satnum"].to_numpy()
            pos_b = gb[["x_km", "y_km", "z_km"]].to_numpy(dtype=float)

            # 1. same-bin pairs
            tree = cKDTree(pos_b)
            pairs = tree.query_pairs(r=threshold_km, output_type="ndarray")  # shape (k,2)

            if pairs.size:
                diffs = pos_b[pairs[:, 0]] - pos_b[pairs[:, 1]]
                dists = np.sqrt(np.sum(diffs * diffs, axis=1))
                for (i, j), dij in zip(pairs, dists):
                    events_buffer.append(
                        {
                            "time_utc": t,
                            "satnum_a": int(sats_b[i]),
                            "satnum_b": int(sats_b[j]),
                            "distance_km": float(dij),
                            "alt_bin_km": int(b),
                        }
                    )

            # 2. cross-bin pairs with adjacent bin
            b2 = b + alt_bin_km
            if b2 in bins:
                gb2 = bins[b2].drop_duplicates(subset=["satnum"], keep="first")
                if len(gb2) == 0:
                    continue

                sats_2 = gb2["satnum"].to_numpy()
                pos_2 = gb2[["x_km", "y_km", "z_km"]].to_numpy(dtype=float)

                cross = _pairs_cross_within_threshold(pos_b, pos_2, threshold_km)
                if len(cross):
                    diffs = pos_b[cross[:, 0]] - pos_2[cross[:, 1]]
                    dists = np.sqrt(np.sum(diffs * diffs, axis=1))
                    for (i, j), dij in zip(cross, dists):
                        events_buffer.append(
                            {
                                "time_utc": t,
                                "satnum_a": int(sats_b[i]),
                                "satnum_b": int(sats_2[j]),
                                "distance_km": float(dij),
                                "alt_bin_km": int(b),
                            }
                        )

        # save to parquet often
        if out_parquet_path and (timesteps_processed % flush_every == 0) and events_buffer:
            chunk = pd.DataFrame.from_records(events_buffer)
            part_path = out_parquet_path.replace(".parquet", f".part{timesteps_processed}.parquet")
            chunk.to_parquet(part_path, index=False)
            events_buffer.clear()

    # final save
    if out_parquet_path and events_buffer:
        chunk = pd.DataFrame.from_records(events_buffer)
        part_path = out_parquet_path.replace(".parquet", ".partFINAL.parquet")
        chunk.to_parquet(part_path, index=False)
        events_buffer.clear()

    if out_parquet_path:
        return pd.DataFrame()

    return pd.DataFrame.from_records(events_buffer)


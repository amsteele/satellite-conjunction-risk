import datetime as dt
import pandas as pd
import os
from load_tle import read_tle_file  # use your actual function name if different
from propagate import make_time_grid, propagate_many
from detect_conjunctions import detect_close_approaches_kdtree


def main():
    # ---- CONFIG ----
    tle_path = "more_satellites.txt"      # make sure this file is in the same folder
    #tle_path = "satellites_nostarlink.txt"      # make sure this file is in the same folder
    hours = 48                             # start small, then increase
    step_minutes = 1.0 
    threshold_km = 5.0                   # closenes of approach
    alt_bin_km = 50.0
    leobound_km = 2000.0
    flush_every = 10

    # ---- LOAD ----
    sat_df = read_tle_file(tle_path)
    print("Loaded satellites:", len(sat_df))

    # ---- TIME GRID ----
    start = dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    times = make_time_grid(start, hours=hours, step_minutes=step_minutes)
    print("Timesteps:", len(times))

    # ---- PROPAGATE ----
    traj_df = propagate_many(sat_df, times, sample_n=len(sat_df))
    print("Trajectory rows:", len(traj_df))
    print("Nonzero sgp4 errors:", (traj_df["sgp4_err"] != 0).sum())

    traj_out = f"data/trajectories_{hours}h_{step_minutes}min.parquet"
    traj_df.to_parquet(traj_out, index=False)
    print("Wrote:", traj_out)

    # ---- DETECT (stream to parquet parts) ----
    events_out = f"data/events_{hours}h_{step_minutes}min_thr{threshold_km:g}.parquet"
    _ = detect_close_approaches_kdtree(
        traj_df=traj_df,
        threshold_km=threshold_km,
        alt_bin_km=alt_bin_km,
        leobound_km=leobound_km,
        out_parquet_path=events_out,
        flush_every=flush_every)
    
    print("Wrote event parts like:", events_out.replace(".parquet", ".part*.parquet"))

    import glob
    parts = sorted(glob.glob(events_out.replace(".parquet", ".part*.parquet")))
    if not parts:
        print("No events found; pair summary not created.")
        return

    events_df = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)

    #parts = sorted(glob.glob(events_out.replace(".parquet", ".part*.parquet")))
    #events_df = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True) if parts else pd.DataFrame()
    #if parts:
    #    events_df = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    #else:
    #    events_df = pd.DataFrame()
    if len(events_df):
        pair_summary = (
            events_df
            .groupby(["satnum_a", "satnum_b"], as_index=False)
            .agg(
                n_detections=("distance_km", "size"),
                min_distance_km=("distance_km", "min"),
                first_time=("time_utc", "min"),
                last_time=("time_utc", "max"),
            )
            .sort_values(["min_distance_km", "n_detections"], ascending=[True, False])
        )
        pair_summary["duration_minutes"] = (
            (pair_summary["last_time"] - pair_summary["first_time"])
            .dt.total_seconds() / 60.0
        )   
        os.system(f"rm -f {events_out.replace('.parquet','')}.part*.parquet")

        pair_summary_path = f"data/pair_summary_thr{threshold_km:g}_{hours}h_{step_minutes}min.parquet"
        pair_summary.to_parquet(pair_summary_path, index=False)
        print("Wrote:", pair_summary_path)
        print(pair_summary.head(10))
    else:
        print("No events found; pair summary not created.")
    manifest_path = "data/latest_run.txt"
    with open(manifest_path, "w") as f:
        f.write(f"traj_path={traj_out}\n")
        f.write(f"events_path={events_out}\n")
        f.write(f"tle_path={tle_path}\n")
        f.write(f"pair_summary_path={pair_summary_path}\n")
        f.write(f"hours={hours}\n")
        f.write(f"step_minutes={step_minutes}\n")
        f.write(f"threshold_km={threshold_km}\n")
        f.write(f"alt_bin_km={alt_bin_km}\n")
        f.write(f"leobound_km={leobound_km}\n")

    print("Wrote run manifest:", manifest_path)

if __name__ == "__main__":
    main()


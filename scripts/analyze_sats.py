import pandas as pd
import matplotlib.pyplot as plt
import run_pipeline as cfg
from load_tle import read_tle_file
import rcparams

def read_sat_piparam(path: str):
    out = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out

run = read_sat_piparam("data/latest_run.txt")

PAIR_SUMMARY_PATH = run["pair_summary_path"]
SAT_PATH = run["tle_path"]
step_min = float(run["step_minutes"])
threshold = float(run["threshold_km"])
pair_summary = pd.read_parquet(PAIR_SUMMARY_PATH)
bad = pair_summary[pair_summary["duration_minutes"] < 0].copy()

print("Negative durations:", len(bad))
print(bad[["satnum_a","satnum_b","first_time","last_time","duration_minutes"]].head(10))

print(
    f"Analyzing: {run.get('hours')}h, "
    f"{run.get('step_minutes')}min, "
    f"thr={run.get('threshold_km')} km"
)

def main():
    pair_summary = pd.read_parquet(PAIR_SUMMARY_PATH)
    
    # --- Add satellite names so we can tag Starlink pairs for plotting ---
    from load_tle import read_tle_file
    
    sat_df = read_tle_file(SAT_PATH)
    sat_name = (
        sat_df[["satnum", "name"]]
        .drop_duplicates(subset=["satnum"])
        .assign(satnum=lambda d: d["satnum"].astype(int))
        .set_index("satnum")["name"]
        )
    sat_meta = sat_df[["satnum", "name"]].drop_duplicates().copy()
    sat_meta["satnum"] = sat_meta["satnum"].astype(int)

    # Attach names to each pair
    pair_summary = pair_summary.reset_index(drop=True)
    pair_summary["name_a"] = pair_summary["satnum_a"].map(sat_name)
    pair_summary["name_b"] = pair_summary["satnum_b"].map(sat_name)

    def is_starlink(name):
        return isinstance(name, str) and "STARLINK" in name.upper()
    
    pair_summary["starlink_a"] = pair_summary["name_a"].map(is_starlink)
    pair_summary["starlink_b"] = pair_summary["name_b"].map(is_starlink)
    #pair_summary["duration_proxy_minutes"] = (
    #     (pair_summary["n_detections"] - 1) * step_minutes
    #     ).clip(lower=0)
    df_ss = pair_summary[pair_summary["starlink_a"] & pair_summary["starlink_b"]]
    df_so = pair_summary[pair_summary["starlink_a"] ^ pair_summary["starlink_b"]]  # mixed pairs
    df_oo = pair_summary[~pair_summary["starlink_a"] & ~pair_summary["starlink_b"]]
    print("Min duration SS:", df_ss["duration_minutes"].min())
    print("Min duration SO:", df_so["duration_minutes"].min())
    print("Min duration OO:", df_oo["duration_minutes"].min())

    # show the worst SO rows if any
    print(df_so.nsmallest(5, "duration_minutes")[["satnum_a","satnum_b","duration_minutes","first_time","last_time"]])
    
    
    # ---- Plot 1: Min distance vs duration ----
    import random
    import numpy as np
    plt.clf()

    fig,ax = plt.subplots(figsize=(8,4))
    #ax.plot(np.linspace(0,threshold,100),np.ones(100)*step_min,'--',color='gray')
    ax.axhspan(0,step_min,facecolor='gray',alpha=0.6,label='region of uncertainty')
    ax.scatter(df_ss["min_distance_km"], [x+random.uniform(0.7,step_min) if x==0 else x for x in df_ss["duration_minutes"]],
            marker="*", color='k', alpha=0.7, s=28, label="Starlink–Starlink")
    ax.scatter(df_so["min_distance_km"], [x+random.uniform(0.7,step_min) if x==0 else x for x in df_so["duration_minutes"]],
            marker="^",color='dodgerblue', alpha=0.6, s=35, label="Starlink–Other")
    ax.scatter(df_oo["min_distance_km"], [x+random.uniform(0.7,step_min) if x==0 else x for x in df_oo["duration_minutes"]],
            marker="s", color='r', alpha=0.6, s=28, label="Other–Other")
    ax.set_yscale('log')
    ax.set_ylim(0.65,3200)
    ax.set_xlim(0,5.05)
    #ax.set_frame_on(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xlabel('Minimum separation (km)',fontsize=14)
    ax.set_ylabel('Encounter duration (minutes)',fontsize=14)
    plt.text(0.03,step_min+0.2,'max measured time, cadence = '+str(step_min)+' mins',fontsize=8)
    plt.title("Satellite encounters by Starlink involvement",fontsize=14)
    plt.legend(frameon=False,bbox_to_anchor=(1,1),fontsize=8)
    plt.tight_layout()
    plt.savefig("min_distance_vs_duration.pdf", dpi=300)
    #plt.show()

    '''
    # ---- Plot 2: Duration distribution ----
    plt.figure()
    plt.yscale('log')
    plt.hist(pair_summary["duration_minutes"], bins=40)
    plt.xlabel("Duration (minutes)")
    plt.ylabel("Number of satellite pairs")
    plt.title("Distribution of close-approach durations")
    plt.tight_layout()
    plt.savefig("duration_distribution.png", dpi=150)
    plt.show()
    plt.clf()
    '''

    # ---- Table: Top persistent encounters ----
    top = pair_summary.sort_values(
        ["duration_minutes", "min_distance_km"],
        ascending=[False, True]
    ).head(10)

    print(top)

    close_pairs = pair_summary[pair_summary["min_distance_km"] <= 1.0].copy()
    print("Pairs with separation ≤ 1 km:", len(close_pairs))
    from load_tle import read_tle_file
    
    sat_meta = sat_df[["satnum", "name"]].drop_duplicates()
    sat_meta["satnum"] = sat_meta["satnum"].astype(int)

    assert sat_meta["satnum"].is_unique

    close_pairs = pair_summary[pair_summary["min_distance_km"] <= 1.0].copy()
    # (or <=5.0 if that’s what you want — but make the print statement match)

    close_pairs = close_pairs.reset_index(drop=True)

    close_pairs["starlink_a"] = close_pairs["name_a"].map(is_starlink)
    close_pairs["starlink_b"] = close_pairs["name_b"].map(is_starlink)


    def pair_type(row):
        if row["starlink_a"] and row["starlink_b"]:
            return "Starlink–Starlink"
        elif row["starlink_a"] or row["starlink_b"]:
            return "Starlink–Non-Starlink"
        else:
            return "Non-Starlink–Non-Starlink"

    close_pairs["pair_type"] = close_pairs.apply(pair_type, axis=1)
    print(close_pairs["pair_type"].value_counts())

    '''
    cols = [
    "name_a", "name_b",
    "min_distance_km",
    "n_detections",
    "duration_minutes",
    "pair_type",
    ]
    
    print(close_pairs[cols].sort_values("min_distance_km").head(20))
    starlink_pairs = close_pairs[close_pairs["pair_type"] == "Starlink–Starlink"]
    print("Starlink–Starlink pairs ≤ 1 km:", len(starlink_pairs))
    
    print(
    starlink_pairs[cols]
    .sort_values("min_distance_km")
    .head(10)
    )
    '''

if __name__ == "__main__":
    main()


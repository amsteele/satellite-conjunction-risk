import datetime as dt
import matplotlib.pyplot as plt
from load_tle import *
from sgp4.api import Satrec,jday

R_EARTH_KM = 6378.137  # Earth equatorial radius (km)

def make_time_grid(start_utc: dt.datetime, hours: int = 48, step_minutes: int = 10):
    # create a list of datetimes

    if start_utc.tzinfo is not None:
        # Convert to naive UTC
        start_utc = start_utc.astimezone(dt.timezone.utc).replace(tzinfo=None)

    n_steps = int((hours * 60) / step_minutes) + 1
    return [start_utc + dt.timedelta(minutes=step_minutes * i) for i in range(n_steps)]

def dt_to_jd_fr(t: dt.datetime):
    # convert a datetime to Julian day (jd) and fractional day (fr) as required by sgp4.

    jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond * 1e-6)
    return jd, fr

def propagate_satrec(sat: Satrec, times_utc):
    # propagate a single Satrec over a list of datetimes.
    # returns arrays: x, y, z (km), altitude (km), error codes.

    xs, ys, zs, alts, errs = [], [], [], [], []

    for t in times_utc:
        jd, fr = dt_to_jd_fr(t)
        e, r, v = sat.sgp4(jd, fr)  # r in km, v in km/s in TEME frame
        errs.append(e)

        if e == 0:
            x, y, z = r
            xs.append(x); ys.append(y); zs.append(z)
            alt = np.linalg.norm(r) - R_EARTH_KM
            alts.append(alt)
        else:
            # If propagation fails at this time, store NaNs for positions/altitude
            xs.append(np.nan); ys.append(np.nan); zs.append(np.nan)
            alts.append(np.nan)

    return np.array(xs), np.array(ys), np.array(zs), np.array(alts), np.array(errs)

def propagate_many(sat_df: pd.DataFrame, times_utc, sample_n: int = 5):
    # propagate N satellites from a dataframe that has at least: ['name','satnum','satrec'].
    # returns a dataframe with one row per satellite-time.

    # Pick a small sample for Day 3 checkpoint
    df = sat_df.copy()
    if len(df) > sample_n:
        df = df.sample(sample_n, random_state=42)

    records = []
    for _, row in df.iterrows():
        sat = row["satrec"]
        name = row.get("name", str(row.get("satnum", "UNKNOWN")))
        satnum = row.get("satnum", None)

        x, y, z, alt, err = propagate_satrec(sat, times_utc)

        for t, xi, yi, zi, alti, ei in zip(times_utc, x, y, z, alt, err):
            records.append({
                "time_utc": t,
                "name": name,
                "satnum": satnum,
                "x_km": xi,
                "y_km": yi,
                "z_km": zi,
                "alt_km": alti,
                "sgp4_err": int(ei),
            })

    out = pd.DataFrame.from_records(records)
    return out



def plot_altitude_timeseries(traj_df: pd.DataFrame, title="Altitude vs Time (sample satellites)"):
    # traj_df is output of propagate_many() with columns: time_utc, name, alt_km

    plt.figure()
    for name, g in traj_df.groupby("name"):
        g = g.sort_values("time_utc")
        plt.plot(g["time_utc"], g["alt_km"], label=name)

    plt.xlabel("Time (UTC)")
    plt.ylabel("Altitude (km)")
    plt.title(title)
    plt.legend(fontsize=8)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
	# 1. Choose a start time (UTC)
	start = dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
	
	# 2. Time grid: 48 hours, every 10 minutes
	times = make_time_grid(start, hours=48, step_minutes=10)

	###   example
	# 3. propagate a small sample for the checkpoint
	traj = propagate_many(test, times, sample_n=5)
	#propagate_many(sat_df: pd.DataFrame, times_utc, sample_n: int = 5)
	
	# 4. quick check
	print("Rows:", len(traj))
	print("Nonzero sgp4 errors:", (traj["sgp4_err"] != 0).sum())
	print(traj.head())
	
	plot_altitude_timeseries(traj)



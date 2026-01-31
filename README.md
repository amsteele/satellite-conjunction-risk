# satellite-conjunction-risk
Satellite Conjunction Risk Analysis Using Public Orbital Data

## Project Goal:

To quantify and visualize the risk of satellite close-approaches in Low Earth Orbit using publicly available orbital data for ~10k satellites, resulting in a reproducible analysis pipeline and shedding light on potential operational risk insights.

## Problem Statement
Low Earth Orbit is getting crowded. Thousands of active satellites now share a relatively small volume of space, and while most objects never come close to one another, a small fraction do. Some of those close approaches are brief, while others persist for hours because satellites share similar orbital planes or are deliberately phased relative to each other.

The goal of this project is not to predict collisions or produce mission-grade conjunction warnings. Instead, the goal is to answer simpler, system-level questions:

- How often do satellites come close to one another when you look across a large population?

- Are close approaches mostly brief, one-off events, or do some pairs remain close for extended periods?

- What does the distribution of “how close” and “for how long” actually look like at scale?

- Do certain types of satellites dominate the smallest-separation events?

By focusing on patterns, persistence, and relative proximity, this project aims to provide a practical, data-driven view of close approaches in LEO that is useful for understanding operational regimes, not just individual events.


## Data Sources
This analysis uses publicly available orbital data only.

Two-Line Element (TLE) sets for active satellites were used as the orbital input.
TLEs are a standard format published by NORAD and distributed by sources such as CelesTrak. They provide a compact representation of satellite orbits suitable for large-scale analysis.

Satellite identifiers and names were taken directly from the TLE data and used to associate close-approach events with specific satellites and operators.

No proprietary tracking data, covariance information, or maneuver data is used. As a result, the analysis reflects what can be learned from open data alone, with all of the associated limitations.

## Methodology
At a high level, the workflow is:

1. Load TLE data for ~10,000 active satellites.

2. Propagate satellite positions forward in time using SGP4.

3. Sample positions at fixed time intervals.

4. Detect close approaches using scalable spatial indexing.

5. Aggregate detections into per-pair summaries.

Each step is intentionally simple and transparent, prioritizing clarity and scalability over fine-grained orbital accuracy.

Because the detection logic is easier to follow when shown step-by-step, the detailed methodology is demonstrated in a Python notebook rather than described exhaustively here.

👉 See: notebooks/methodology_overview.ipynb

## Results
![Example encounter frequency](examples/example_48hours_5km_encounters.gif)


| Satellite 1   | Satellite 2    |   Min Distance (km) |   # Detections |   Duration (min) | Pair Type         |
|:---------------|:---------------|------------------:|---------------:|-------------------:|:------------------|
| STARLINK-34024 | STARLINK-34111 |             0.192 |             27 |            260.000 | Starlink–Starlink |
| STARLINK-34571 | STARLINK-34643 |             0.471 |             13 |            130.000 | Starlink–Starlink |
| STARLINK-31888 | STARLINK-33677 |             0.522 |              1 |              0.000 | Starlink–Starlink |
| STARLINK-34362 | STARLINK-34374 |             0.538 |             15 |            170.000 | Starlink–Starlink |
| STARLINK-34495 | STARLINK-34478 |             0.565 |             20 |            190.000 | Starlink–Starlink |
| STARLINK-35652 | STARLINK-35672 |             0.573 |              9 |             80.000 | Starlink–Starlink |
| STARLINK-32667 | STARLINK-35502 |             0.645 |              1 |              0.000 | Starlink–Starlink |
| STARLINK-33986 | STARLINK-33858 |             0.653 |             18 |            170.000 | Starlink–Starlink |
| STARLINK-32912 | STARLINK-32925 |             0.658 |             21 |            200.000 | Starlink–Starlink |
| STARLINK-32403 | STARLINK-32625 |             0.708 |              1 |              0.000 | Starlink–Starlink |
| STARLINK-5332  | STARLINK-5296  |             0.713 |              4 |            150.000 | Starlink–Starlink |
| STARLINK-34380 | STARLINK-34357 |             0.732 |             20 |            190.000 | Starlink–Starlink |
| STARLINK-35681 | STARLINK-35669 |             0.855 |             10 |             90.000 | Starlink–Starlink |
| STARLINK-5859  | STARLINK-5871  |             0.868 |             12 |            110.000 | Starlink–Starlink |
| STARLINK-6096  | STARLINK-30857 |             0.870 |              1 |              0.000 | Starlink–Starlink |
| STARLINK-35343 | STARLINK-36486 |             0.870 |              9 |             80.000 | Starlink–Starlink |
| STARLINK-35690 | STARLINK-35662 |             0.901 |             12 |            120.000 | Starlink–Starlink |
| STARLINK-34407 | STARLINK-34457 |             0.928 |             29 |            280.000 | Starlink–Starlink |
| STARLINK-6171  | STARLINK-30551 |             0.940 |              1 |              0.000 | Starlink–Starlink |
| STARLINK-3989  | STARLINK-5200  |             0.955 |              1 |              0.000 | Starlink–Starlink |

## Limitations & Assumptions 

This analysis is intended to provide a comparative, exploration of satellite close approaches (rather than mission-grade conjunction assessments). The following assumptions and limitations should be considered when interpreting the results:

**Discrete temporal sampling**: Satellite positions are propagated and evaluated at fixed 10-minute intervals. Reported minimum separations therefore represent the closest sampled distance, not a continuously optimized time of closest approach. True minima may be smaller than reported values.

**TLE-based propagation**: Orbits are propagated using publicly available Two-Line Element (TLE) data and the SGP4 model. TLEs have inherent uncertainties that grow with time from epoch and are not suitable for precise conjunction prediction without additional tracking data.

**Simplified proximity metric**: Close approaches are identified using three-dimensional Euclidean separation in the SGP4 TEME reference frame. Effects such as covariance, relative velocity, and collision probability are not considered.

**Altitude-binned candidate selection**: To enable scalable analysis across thousands of satellites, candidate pairs are pre-filtered using altitude bins. While adjacent-bin comparisons are included, this approach prioritizes computational efficiency over exhaustive geometric evaluation.

**Operational scope**: Persistent, small-separation encounters within large constellations (e.g., Starlink) are interpreted as controlled co-orbital configurations rather than unmanaged collision risk. This analysis does not attempt to distinguish maneuver planning, station-keeping intent, or operator-specific mitigation strategies.

Despite these limitations, the methodology is sufficient to identify patterns, persistence, and relative risk regimes across large satellite populations, which is the primary goal of this project.

"""
Field drawing and drill plot, adapted from Will's notebook (src/local_eda_wgaty.ipynb).

Changes from the notebook version:
- The field is its own figure. Speed and acceleration are drawn as two separate interactive
  charts on the Drill Viewer page instead of one chart with two y-axes.
- Direction arrows use the NFL tracking convention (0 deg = +y, clockwise), so dx = sin, dy = cos.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle
from mpl_toolkits.axes_grid1 import make_axes_locatable


def draw_nfl_field(ax, x_min=0, x_max=120, y_max=53.333):
    """Draw a clean top-down NFL field in yards."""
    ax.set_facecolor("#2e6f40")
    ax.add_patch(Rectangle((0, 0), 10, y_max, facecolor="#245932", edgecolor="none"))
    ax.add_patch(Rectangle((110, 0), 10, y_max, facecolor="#245932", edgecolor="none"))

    for x in range(10, 111, 5):
        lw = 1.5 if x % 10 == 0 else 0.7
        alpha = 0.85 if x % 10 == 0 else 0.45
        ax.axvline(x, color="white", linewidth=lw, alpha=alpha)

    ax.plot([x_min, x_max], [0, 0], color="white", lw=2)
    ax.plot([x_min, x_max], [y_max, y_max], color="white", lw=2)
    ax.plot([0, 0], [0, y_max], color="white", lw=2)
    ax.plot([120, 120], [0, y_max], color="white", lw=2)

    for yard_line in range(20, 101, 10):
        label = str(yard_line - 10 if yard_line <= 60 else 110 - yard_line)
        ax.text(yard_line, 6, label, color="white", fontsize=9,
                ha="center", va="center", alpha=0.75, fontweight="bold", clip_on=True)
        ax.text(yard_line, y_max - 6, label, color="white", fontsize=9,
                ha="center", va="center", alpha=0.75, fontweight="bold", rotation=180, clip_on=True)

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0, y_max)
    ax.set_xlabel("Field length x (yards)")
    ax.set_ylabel("Field width y (yards)")
    ax.set_aspect("equal")


def path_length(df: pd.DataFrame) -> float:
    """Distance traveled in yards, measured from the x/y path (the `dis` column is much smaller than per-frame yards)."""
    return float(np.hypot(df["x"].diff(), df["y"].diff()).sum())


def plot_drill_path(df: pd.DataFrame, title: str = "Combine drill", zoom: bool = True):
    """Top-down field with the player's path colored by speed and direction arrows every 0.5 s."""
    df = df.sort_values("time").reset_index(drop=True)
    total_dist = path_length(df)

    fig, ax = plt.subplots(figsize=(12, 6))
    draw_nfl_field(ax)
    if zoom:
        pad = 5
        ax.set_xlim(max(0, df["x"].min() - pad), min(120, df["x"].max() + pad))
        ax.set_ylim(max(0, df["y"].min() - pad), min(53.333, df["y"].max() + pad))

    points = np.array([df["x"].values, df["y"].values]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    lc = LineCollection(segments, cmap="plasma", norm=plt.Normalize(df["s"].min(), df["s"].max()), linewidth=3.2)
    lc.set_array(df["s"].values[:-1])
    line = ax.add_collection(lc)
    cax = make_axes_locatable(ax).append_axes("right", size="2%", pad=0.1)  # color bar matches field height
    fig.colorbar(line, cax=cax).set_label("Speed (yd/s)")

    ax.scatter(df["x"].iloc[0], df["y"].iloc[0], color="limegreen", s=70, zorder=5, label="Start")
    ax.scatter(df["x"].iloc[-1], df["y"].iloc[-1], color="crimson", s=70, zorder=5, label="End")

    sub = df.iloc[::5]  # every 0.5 s at 10 Hz
    rad = np.deg2rad(sub["dir"].values)
    ax.quiver(sub["x"], sub["y"], np.sin(rad) * 1.4, np.cos(rad) * 1.4,
              angles="xy", scale_units="xy", scale=1, color="white",
              edgecolor="black", linewidth=0.5, width=0.0035, zorder=4)
    ax.set_title(f"{title} (total distance {total_dist:.1f} yd)")
    ax.legend(loc="best")
    return fig

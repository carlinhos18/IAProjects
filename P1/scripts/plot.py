"""
graphs.py — Score-vs-ParamVariant and Time-vs-ParamVariant plots.

One figure per (algorithm x varied_param), two subplots: Score | Time.
Each dataset is a separate coloured line.

For genetic_algorithm figures, the baseline point (default config:
pop_size=20, generations=30, mutation_rate=0.03, elite_individ=5)
is marked with a ★ on its line per dataset. If that exact value is not
in the current group's x-axis it is looked up from the generations group
and plotted as a separate annotated scatter point.

Output: logs/graphs/<algorithm>_<varied_param>.png

Usage:
    python3 graphs.py [file1.csv file2.csv ...]

Requires:
    pip install matplotlib pandas
"""

import sys
import os

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
except ImportError as exc:
    sys.exit("[ERROR] Missing dependency: {}\n  pip install matplotlib pandas".format(exc))

# ─────────────────────────────────────────────────────────────────────────────
# Path resolution
# ─────────────────────────────────────────────────────────────────────────────

def _find_root():
    candidate = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(candidate, "logs")):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent
    return os.path.dirname(os.path.abspath(__file__))

ROOT    = _find_root()
OUT_DIR = os.path.join(ROOT, "logs", "graphs")
os.makedirs(OUT_DIR, exist_ok=True)

def find_csvs():
    if len(sys.argv) > 1:
        return sys.argv[1:]
    log_dir = os.path.join(ROOT, "logs")
    found = sorted(
        os.path.join(log_dir, f)
        for f in os.listdir(log_dir)
        if f.endswith(".csv")
    )
    if not found:
        sys.exit("[ERROR] No CSV files found in {}\n  Run benchmark.py first.".format(log_dir))
    return found

# ─────────────────────────────────────────────────────────────────────────────
# Genetic baseline defaults
# These are the values that represent "nothing changed" for each param.
# pop_size=20 is the reference; it lives in the generations group.
# ─────────────────────────────────────────────────────────────────────────────

GENETIC_DEFAULTS = {
    "generations":  30.0,
    "pop_size":     20.0,
    "mutation_rate": 0.03,
    "elite_individ": 5.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# Style
# ─────────────────────────────────────────────────────────────────────────────

DATASET_COLOURS = {
    "b_read_on":       "#1f77b4",
    "c_incunabula":    "#ff7f0e",
    "d_tough_choices": "#2ca02c",
}
FALLBACK = ["#9467bd", "#d62728", "#8c564b", "#e377c2", "#17becf"]
MARKERS  = ["o", "s", "D", "^", "v"]

plt.rcParams.update({
    "figure.facecolor":  "white",
    "axes.facecolor":    "white",
    "axes.edgecolor":    "#cccccc",
    "axes.labelcolor":   "black",
    "axes.titlecolor":   "black",
    "axes.titlesize":    11,
    "axes.labelsize":    10,
    "axes.grid":         True,
    "grid.color":        "#e5e5e5",
    "grid.linewidth":    0.8,
    "xtick.color":       "#444444",
    "ytick.color":       "#444444",
    "xtick.labelsize":   9,
    "ytick.labelsize":   9,
    "legend.facecolor":  "white",
    "legend.edgecolor":  "#cccccc",
    "legend.fontsize":   9,
    "text.color":        "black",
    "figure.dpi":        120,
    "savefig.dpi":       150,
    "savefig.facecolor": "white",
    "lines.linewidth":   2.0,
    "lines.markersize":  7,
})

def ds_colour(name, idx):
    return DATASET_COLOURS.get(name, FALLBACK[idx % len(FALLBACK)])

def fmt_score(x, _):
    if x >= 1_000_000:
        return "{:.2f}M".format(x / 1_000_000)
    if x >= 1_000:
        return "{:.0f}K".format(x / 1_000)
    return str(int(x))

def fmt_time(x, _):
    if x >= 3600:
        return "{:.1f}h".format(x / 3600)
    if x >= 60:
        return "{:.1f}m".format(x / 60)
    return "{:.2f}s".format(x)

def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

def finish_ax(ax, title, xlabel, ylabel, xticks, formatter):
    ax.set_title(title, pad=10)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.yaxis.set_major_formatter(formatter)
    ax.set_xticks(xticks)
    ax.set_xticklabels([str(x) for x in xticks], rotation=30, ha="right")
    ax.legend(loc="best", framealpha=0.9)
    style_ax(ax)

def save_fig(fig, name):
    path = os.path.join(OUT_DIR, "{}.png".format(name))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("  [saved] {}".format(path))

# ─────────────────────────────────────────────────────────────────────────────
# Load & parse
# ─────────────────────────────────────────────────────────────────────────────

def load(csv_paths):
    frames = []
    for p in csv_paths:
        if not os.path.isfile(p):
            print("  [WARN] not found: {}".format(p))
            continue
        frames.append(pd.read_csv(p))
    if not frames:
        sys.exit("[ERROR] No readable CSV files.")

    df = pd.concat(frames, ignore_index=True)
    df.columns = df.columns.str.strip()
    df["score"]         = pd.to_numeric(df["score"],         errors="coerce")
    df["runtime_s"]     = pd.to_numeric(df["runtime_s"],     errors="coerce")
    df["param_variant"] = pd.to_numeric(df["param_variant"], errors="coerce")
    df = df.dropna(subset=["score", "runtime_s"])

    def extract_value(row):
        vp = str(row["varied_param"]).strip()
        for part in str(row["parameters"]).split(";"):
            k, _, v = part.strip().partition("=")
            if k.strip() == vp:
                try:
                    return float(v.strip())
                except ValueError:
                    pass
        return float(row["param_variant"])

    df["varied_value"] = df.apply(extract_value, axis=1)
    return df

# ─────────────────────────────────────────────────────────────────────────────
# Generic plot (non-genetic algorithms)
# ─────────────────────────────────────────────────────────────────────────────

def plot_group(algo, varied_param, group_df):
    datasets = sorted(group_df["dataset"].unique())
    all_xs   = sorted(group_df["varied_value"].unique())

    fig, (ax_score, ax_time) = plt.subplots(
        1, 2, figsize=(13, 4.6),
        gridspec_kw={"wspace": 0.38},
    )
    fig.suptitle(
        "{} — {}".format(algo.replace("_", " ").title(), varied_param),
        fontsize=13, fontweight="bold",
    )

    for idx, dataset in enumerate(datasets):
        sub    = group_df[group_df["dataset"] == dataset].sort_values("varied_value")
        xs     = sub["varied_value"].tolist()
        scores = sub["score"].tolist()
        times  = sub["runtime_s"].tolist()
        colour = ds_colour(dataset, idx)
        marker = MARKERS[idx % len(MARKERS)]
        label  = dataset.replace("_", " ")

        ax_score.plot(xs, scores, color=colour, marker=marker, label=label, zorder=3)
        for x, y in zip(xs, scores):
            ax_score.annotate(
                fmt_score(y, None), (x, y),
                textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=7.5, color=colour,
            )

        ax_time.plot(xs, times, color=colour, marker=marker, label=label, zorder=3)
        for x, y in zip(xs, times):
            ax_time.annotate(
                fmt_time(y, None), (x, y),
                textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=7.5, color=colour,
            )

    finish_ax(ax_score, "Score vs {}".format(varied_param), varied_param, "Score",
              all_xs, mticker.FuncFormatter(fmt_score))
    finish_ax(ax_time,  "Runtime vs {}".format(varied_param), varied_param, "Time",
              all_xs, mticker.FuncFormatter(fmt_time))

    save_fig(fig, "{}_{}".format(algo, varied_param))

# ─────────────────────────────────────────────────────────────────────────────
# Genetic plot — baseline ★ looked up from the full genetic dataframe
# ─────────────────────────────────────────────────────────────────────────────

def _get_baseline(dataset, varied_param, genetic_df):
    """
    Return (base_x, base_score, base_time) for the shared default config.
    Looks in the current group first, then falls back to the generations group.
    """
    default_val = GENETIC_DEFAULTS.get(varied_param)

    sub = genetic_df[
        (genetic_df["dataset"] == dataset) &
        (genetic_df["varied_param"] == varied_param) &
        (genetic_df["varied_value"] == default_val)
    ]
    if not sub.empty:
        row = sub.iloc[0]
        return float(default_val), float(row["score"]), float(row["runtime_s"])

    fallback = genetic_df[
        (genetic_df["dataset"] == dataset) &
        (genetic_df["varied_param"] == "generations") &
        (genetic_df["varied_value"] == GENETIC_DEFAULTS["generations"])
    ]
    if not fallback.empty:
        row = fallback.iloc[0]
        return float(default_val), float(row["score"]), float(row["runtime_s"])

    return None, None, None


def plot_genetic_group(varied_param, group_df, genetic_df):
    import bisect
    datasets    = sorted(group_df["dataset"].unique())
    default_val = GENETIC_DEFAULTS.get(varied_param)

    fig, (ax_score, ax_time) = plt.subplots(
        1, 2, figsize=(13, 4.6),
        gridspec_kw={"wspace": 0.38},
    )
    fig.suptitle(
        "Genetic Algorithm — {}".format(varied_param),
        fontsize=13, fontweight="bold",
    )

    all_xs_set = set(group_df["varied_value"].unique())
    star_in_legend = False

    for idx, dataset in enumerate(datasets):
        sub    = group_df[group_df["dataset"] == dataset].sort_values("varied_value")
        xs     = sub["varied_value"].tolist()
        scores = sub["score"].tolist()
        times  = sub["runtime_s"].tolist()
        colour = ds_colour(dataset, idx)
        marker = MARKERS[idx % len(MARKERS)]
        label  = dataset.replace("_", " ")

        base_x, base_score, base_time = _get_baseline(dataset, varied_param, genetic_df)

        # Inject baseline into the data series if not already present,
        # so the line passes through it as a real connected point.
        if base_x is not None and base_x not in xs:
            pos = bisect.bisect_left(xs, base_x)
            xs.insert(pos, base_x)
            scores.insert(pos, base_score)
            times.insert(pos, base_time)
            all_xs_set.add(base_x)

        # Score line
        ax_score.plot(xs, scores, color=colour, marker=marker, label=label, zorder=3)
        for x, y in zip(xs, scores):
            ax_score.annotate(
                fmt_score(y, None), (x, y),
                textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=7.5, color=colour,
            )

        # Time line
        ax_time.plot(xs, times, color=colour, marker=marker, label=label, zorder=3)
        for x, y in zip(xs, times):
            ax_time.annotate(
                fmt_time(y, None), (x, y),
                textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=7.5, color=colour,
            )

        # Star on baseline point
        if base_x is not None:
            star_label = "Baseline (★, {}={})".format(varied_param, default_val) if not star_in_legend else "_nolegend_"
            ax_score.plot(
                [base_x], [base_score],
                marker="*", markersize=16,
                color=colour, markeredgecolor="black", markeredgewidth=0.5,
                linestyle="none", zorder=6, label=star_label,
            )
            ax_time.plot(
                [base_x], [base_time],
                marker="*", markersize=16,
                color=colour, markeredgecolor="black", markeredgewidth=0.5,
                linestyle="none", zorder=6, label="_nolegend_",
            )
            star_in_legend = True

    tick_xs = sorted(all_xs_set)

    finish_ax(ax_score, "Score vs {}".format(varied_param), varied_param, "Score",
              tick_xs, mticker.FuncFormatter(fmt_score))
    finish_ax(ax_time,  "Runtime vs {}".format(varied_param), varied_param, "Time",
              tick_xs, mticker.FuncFormatter(fmt_time))

    fig.text(
        0.5, -0.02,
        "★  baseline: pop_size=20, generations=30, mutation_rate=0.03, elite_individ=5",
        ha="center", fontsize=8.5, color="#555555",
    )

    save_fig(fig, "genetic_algorithm_{}".format(varied_param))

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    csv_paths = find_csvs()

    print("\n  Book-Scanning — Graph Generator")
    print("  Sources : {}".format(", ".join(os.path.basename(p) for p in csv_paths)))
    print("  Output  : {}\n".format(OUT_DIR))

    df = load(csv_paths)

    # Full genetic dataframe — used for baseline lookups across groups
    genetic_df = df[df["algorithm"] == "genetic_algorithm"].copy()

    groups = df.groupby(["algorithm", "varied_param"])
    print("  Figures to generate: {}\n".format(len(groups)))

    for (algo, varied_param), group in sorted(groups):
        print("  Plotting {} / {}".format(algo, varied_param))
        if algo == "genetic_algorithm":
            plot_genetic_group(varied_param, group, genetic_df)
        else:
            plot_group(algo, varied_param, group)

    print("\n  Done — {} figures saved to {}".format(len(groups), OUT_DIR))

if __name__ == "__main__":
    main()
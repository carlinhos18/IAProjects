from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt


def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _read_rows(csv_path: Path) -> Dict[str, List[Dict[str, str]]]:
    grouped: Dict[str, List[Dict[str, str]]] = {}

    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            dataset = row.get("dataset", "unknown")
            grouped.setdefault(dataset, []).append(row)

    for dataset in grouped:
        grouped[dataset].sort(key=lambda row: int(row.get("run", "0")))

    return grouped


def _baseline_vs_average(rows: List[Dict[str, str]]) -> Tuple[float, float, int]:
    if not rows:
        return float("nan"), float("nan"), 0

    baseline_score = _to_float(rows[0].get("score", ""))

    compare_rows = rows[1:4]
    if not compare_rows:
        compare_rows = [rows[0]]

    avg_score = sum(_to_float(row.get("score", "")) for row in compare_rows) / len(compare_rows)
    return baseline_score, avg_score, len(compare_rows)


def _baseline_vs_average_runtime(rows: List[Dict[str, str]]) -> Tuple[float, float, int]:
    if not rows:
        return float("nan"), float("nan"), 0

    baseline_runtime = _to_float(rows[0].get("runtime_s", ""))

    compare_rows = rows[1:4]
    if not compare_rows:
        compare_rows = [rows[0]]

    avg_runtime = sum(_to_float(row.get("runtime_s", "")) for row in compare_rows) / len(compare_rows)
    return baseline_runtime, avg_runtime, len(compare_rows)


def _relative_difference_percent(baseline: float, average: float) -> float:
    if baseline == 0 or baseline != baseline or average != average:
        return float("nan")
    return ((average - baseline) / baseline) * 100.0


def _annotate_bars(ax: plt.Axes, bars, values: List[float], suffix: str = "") -> None:
    for bar, value in zip(bars, values):
        if value != value:
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height(),
            f"{value:,.0f}{suffix}".replace(",", " "),
            ha="center",
            va="bottom",
            fontsize=8,
        )


def _annotate_percentage_bars(ax: plt.Axes, bars, values: List[float]) -> None:
    for bar, value in zip(bars, values):
        if value != value:
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height(),
            f"{value:+.2f}%",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=8,
        )


def generate_baseline_genetic_graph() -> Tuple[Path, Path, Path, Path]:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    csv_path = project_dir / "logs" / "baseline_genetic.csv"
    output_dir = project_dir / "logs" / "graphs"
    output_dir.mkdir(parents=True, exist_ok=True)

    grouped = _read_rows(csv_path)

    datasets = []
    baseline_scores = []
    average_scores = []
    compare_counts = []
    baseline_runtimes = []
    average_runtimes = []
    score_deltas_pct = []
    runtime_deltas_pct = []

    for dataset in sorted(grouped.keys()):
        baseline_score, avg_score, used_count = _baseline_vs_average(grouped[dataset])
        baseline_runtime, avg_runtime, _ = _baseline_vs_average_runtime(grouped[dataset])
        datasets.append(dataset)
        baseline_scores.append(baseline_score)
        average_scores.append(avg_score)
        compare_counts.append(used_count)
        baseline_runtimes.append(baseline_runtime)
        average_runtimes.append(avg_runtime)
        score_deltas_pct.append(_relative_difference_percent(baseline_score, avg_score))
        runtime_deltas_pct.append(_relative_difference_percent(baseline_runtime, avg_runtime))

    x_positions = list(range(len(datasets)))
    bar_width = 0.36

    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.bar(
        [x - bar_width / 2 for x in x_positions],
        baseline_scores,
        width=bar_width,
        label="baseline (1a linha)",
        color="#4c78a8",
        edgecolor="black",
        linewidth=0.5,
    )
    ax.bar(
        [x + bar_width / 2 for x in x_positions],
        average_scores,
        width=bar_width,
        label="media das linhas 2-4",
        color="#f58518",
        edgecolor="black",
        linewidth=0.5,
    )

    ax.set_title("Baseline Genetic | Score absoluto")
    ax.set_ylabel("score")
    ax.set_xticks(x_positions)
    ax.set_xticklabels(datasets)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="best")
    _annotate_bars(ax, ax.containers[0], baseline_scores)
    _annotate_bars(ax, ax.containers[1], average_scores)

    for idx, count in enumerate(compare_counts):
        ax.text(
            idx,
            max(baseline_scores[idx], average_scores[idx]),
            f"n={count}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    fig.tight_layout()
    score_output = output_dir / "baseline_genetic_score_comparison.png"
    fig.savefig(score_output, dpi=180)
    plt.close(fig)

    fig_score_delta, ax_score_delta = plt.subplots(figsize=(10, 5.8))
    score_delta_bars = ax_score_delta.bar(
        datasets,
        score_deltas_pct,
        color="#7f7f7f",
        edgecolor="black",
        linewidth=0.5,
    )
    ax_score_delta.axhline(0, color="black", linewidth=1)
    ax_score_delta.set_title("Baseline Genetic | Variação percentual do score")
    ax_score_delta.set_ylabel("Δ score vs baseline (%)")
    ax_score_delta.grid(axis="y", alpha=0.3)
    _annotate_percentage_bars(ax_score_delta, score_delta_bars, score_deltas_pct)
    fig_score_delta.tight_layout()
    score_delta_output = output_dir / "baseline_genetic_score_delta_percent.png"
    fig_score_delta.savefig(score_delta_output, dpi=180)
    plt.close(fig_score_delta)

    fig_rt, ax_rt = plt.subplots(figsize=(10, 5.8))

    ax_rt.bar(
        [x - bar_width / 2 for x in x_positions],
        baseline_runtimes,
        width=bar_width,
        label="baseline (1a linha)",
        color="#54a24b",
        edgecolor="black",
        linewidth=0.5,
    )
    ax_rt.bar(
        [x + bar_width / 2 for x in x_positions],
        average_runtimes,
        width=bar_width,
        label="media das linhas 2-4",
        color="#e45756",
        edgecolor="black",
        linewidth=0.5,
    )

    ax_rt.set_title("Baseline Genetic | Runtime absoluto")
    ax_rt.set_ylabel("runtime (s)")
    ax_rt.set_xticks(x_positions)
    ax_rt.set_xticklabels(datasets)
    ax_rt.grid(axis="y", alpha=0.3)
    ax_rt.legend(loc="best")
    _annotate_bars(ax_rt, ax_rt.containers[0], baseline_runtimes, suffix="s")
    _annotate_bars(ax_rt, ax_rt.containers[1], average_runtimes, suffix="s")

    fig_rt.tight_layout()
    runtime_output = output_dir / "baseline_genetic_runtime_comparison.png"
    fig_rt.savefig(runtime_output, dpi=180)
    plt.close(fig_rt)

    fig_rt_delta, ax_rt_delta = plt.subplots(figsize=(10, 5.8))
    runtime_delta_bars = ax_rt_delta.bar(
        datasets,
        runtime_deltas_pct,
        color="#9c755f",
        edgecolor="black",
        linewidth=0.5,
    )
    ax_rt_delta.axhline(0, color="black", linewidth=1)
    ax_rt_delta.set_title("Baseline Genetic | Variação percentual do runtime")
    ax_rt_delta.set_ylabel("Δ runtime vs baseline (%)")
    ax_rt_delta.grid(axis="y", alpha=0.3)
    _annotate_percentage_bars(ax_rt_delta, runtime_delta_bars, runtime_deltas_pct)
    fig_rt_delta.tight_layout()
    runtime_delta_output = output_dir / "baseline_genetic_runtime_delta_percent.png"
    fig_rt_delta.savefig(runtime_delta_output, dpi=180)
    plt.close(fig_rt_delta)

    return score_output, score_delta_output, runtime_output, runtime_delta_output


def main() -> None:
    score_output, score_delta_output, runtime_output, runtime_delta_output = generate_baseline_genetic_graph()
    print(f"Created: {score_output}")
    print(f"Created: {score_delta_output}")
    print(f"Created: {runtime_output}")
    print(f"Created: {runtime_delta_output}")


if __name__ == "__main__":
    main()

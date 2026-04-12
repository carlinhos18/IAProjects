from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt


def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _extract_param_value(parameters: str, param_name: str) -> float:
    parts = [part.strip() for part in parameters.split(";")]
    for part in parts:
        if "=" not in part:
            continue
        key, value = [piece.strip() for piece in part.split("=", 1)]
        if key == param_name:
            return _to_float(value)
    return float("nan")


def _read_algorithm_rows(csv_path: Path, algorithm: str) -> Tuple[str, List[Dict[str, str]]]:
    rows: List[Dict[str, str]] = []
    varied_param = "param"

    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if row.get("algorithm") != algorithm:
                continue
            varied_param = row.get("varied_param", "param")
            rows.append(row)

    if not rows:
        raise ValueError(f"No rows found for algorithm '{algorithm}' in {csv_path}")

    return varied_param, rows


def generate_hill_annealing_graphs(algorithm: str) -> Tuple[Path, Path]:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    csv_path = project_dir / "logs" / "results_hill_annealing.csv"
    output_dir = project_dir / "logs" / "graphs"
    output_dir.mkdir(parents=True, exist_ok=True)

    varied_param, rows = _read_algorithm_rows(csv_path=csv_path, algorithm=algorithm)

    grouped: Dict[str, List[Tuple[float, float, float]]] = defaultdict(list)
    best_score_points: Dict[str, Tuple[float, float]] = {}

    for row in rows:
        dataset = row.get("dataset", "unknown")
        param_value = _extract_param_value(row.get("parameters", ""), varied_param)
        score = _to_float(row.get("score", ""))
        runtime = _to_float(row.get("runtime_s", ""))
        grouped[dataset].append((param_value, score, runtime))

        current_best = best_score_points.get(dataset)
        if current_best is None or score > current_best[1]:
            best_score_points[dataset] = (param_value, score)

    for dataset in grouped:
        grouped[dataset].sort(key=lambda item: item[0])

    fig_time, ax_time = plt.subplots(figsize=(9, 5.5))
    for dataset in sorted(grouped.keys()):
        xs = [item[0] for item in grouped[dataset]]
        ys = [item[2] for item in grouped[dataset]]
        ax_time.plot(xs, ys, marker="o", linewidth=2, label=dataset)

    ax_time.set_title(f"{algorithm} | Tempo em funcao do parametro")
    ax_time.set_xlabel(varied_param)
    ax_time.set_ylabel("runtime (s)")
    ax_time.grid(alpha=0.3)
    ax_time.legend(loc="best")
    fig_time.tight_layout()

    time_output = output_dir / f"{algorithm}_time_vs_param.png"
    fig_time.savefig(time_output, dpi=180)
    plt.close(fig_time)

    fig_score, ax_score = plt.subplots(figsize=(9, 5.5))
    for dataset in sorted(grouped.keys()):
        xs = [item[0] for item in grouped[dataset]]
        ys = [item[1] for item in grouped[dataset]]
        line, = ax_score.plot(xs, ys, marker="o", linewidth=2, label=dataset)

        best_point = best_score_points.get(dataset)
        if best_point is not None:
            ax_score.scatter(
                [best_point[0]],
                [best_point[1]],
                marker="*",
                s=280,
                color=line.get_color(),
                edgecolors="black",
                linewidths=1.0,
                label=f"melhor score ({dataset})",
                zorder=5,
            )

    ax_score.set_title(f"{algorithm} | Score em funcao do parametro")
    ax_score.set_xlabel(varied_param)
    ax_score.set_ylabel("score")
    ax_score.grid(alpha=0.3)
    ax_score.legend(loc="best")
    fig_score.tight_layout()

    score_output = output_dir / f"{algorithm}_score_vs_param.png"
    fig_score.savefig(score_output, dpi=180)
    plt.close(fig_score)

    return time_output, score_output


def main(algorithm: str) -> None:
    time_output, score_output = generate_hill_annealing_graphs(algorithm=algorithm)
    print(f"Created: {time_output}")
    print(f"Created: {score_output}")

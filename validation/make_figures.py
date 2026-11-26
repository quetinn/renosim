"""Draw the figures of the validation note from the committed result files.

Every figure is built from the aggregated JSON files of ``validation/report/``
(no raw ADEME data is needed), so anyone can regenerate them after cloning:

    pip install -r validation/requirements.txt
    python validation/make_figures.py

Outputs: SVG files in ``validation/report/figures/`` (small, committed).
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

REPORT = Path(__file__).parent / "report"
FIGURES = REPORT / "figures"
LABELS = ["A", "B", "C", "D", "E", "F", "G"]

# Palette: one accent for the reference series, a muted one for comparisons.
INK = "#1f2933"
MUTED = "#8a97a6"
ACCENT = "#1f6f8b"
WARN = "#c2410c"
GRID = "#e4e7eb"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": INK,
        "ytick.color": INK,
        "svg.fonttype": "none",  # keep text as text (searchable, lighter)
        "svg.hashsalt": "renosim",  # deterministic ids -> stable diffs
    }
)


def load(name: str) -> dict:
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def fr(x: float, digits: int = 1) -> str:
    """French decimal formatting."""
    return f"{x:.{digits}f}".replace(".", ",")


def save(fig: plt.Figure, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name, format="svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)
    print(f"-> {FIGURES / name}")


def confusion(results: dict, name: str, title: str) -> None:
    """Row-normalised label confusion matrix (observed rows, predicted columns)."""
    matrix = results["confusion_matrix_obs_rows_pred_cols"]
    counts = [[matrix[o][p] for p in LABELS] for o in LABELS]
    shares = [[c / max(sum(row), 1) for c in row] for row in counts]
    cmap = LinearSegmentedColormap.from_list("renosim", ["#ffffff", ACCENT])
    fig, ax = plt.subplots(figsize=(5.4, 4.6))
    ax.imshow(shares, cmap=cmap, vmin=0, vmax=1)
    for i, row in enumerate(shares):
        for j, share in enumerate(row):
            if counts[i][j] == 0:
                continue
            ax.text(
                j,
                i,
                f"{round(share * 100)} %",
                ha="center",
                va="center",
                fontsize=8.5,
                color="white" if share > 0.5 else INK,
            )
    # +/-1 class band
    for k in range(len(LABELS)):
        ax.add_patch(
            plt.Rectangle(
                (max(k - 1, 0) - 0.5, k - 0.5),
                min(k + 1, 6) - max(k - 1, 0) + 1,
                1,
                fill=False,
                edgecolor=WARN,
                linewidth=0.6,
                linestyle=":",
            )
        )
    ax.set_xticks(range(7), LABELS)
    ax.set_yticks(range(7), LABELS)
    ax.set_xlabel("Étiquette prédite par RénoSim")
    ax.set_ylabel("Étiquette du DPE officiel")
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0)
    exact = results["label_exact_agreement"] * 100
    within = results["label_within_one_class"] * 100
    ax.set_title(
        f"{title}\nexact {fr(exact)} % · ±1 classe {fr(within)} % (pointillés)",
        fontsize=10,
        color=INK,
        loc="left",
    )
    save(fig, name)


def by_stratum(results: dict, name: str) -> None:
    """+/-1 class agreement by construction period and by heating energy (test)."""
    order = [
        "avant 1948",
        "1948-1974",
        "1975-1977",
        "1978-1982",
        "1983-1988",
        "1989-2000",
        "2001-2005",
        "2006-2012",
        "2013-2021",
        "après 2021",
    ]
    energy_names = {
        "Électricité": "Électricité",
        "Bois – Bûches": "Bois bûches",  # noqa: RUF001 - exact ADEME value (en dash)
        "Bois – Granulés (pellets) ou briquettes": "Granulés",  # noqa: RUF001
        "Fioul domestique": "Fioul",
        "Gaz naturel": "Gaz naturel",
    }
    periods = results["by_stratum"]["periode"]
    energies = results["by_stratum"]["energie"]
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(9.2, 3.8), gridspec_kw={"width_ratios": [2, 1.1]}, sharey=True
    )
    for ax, keys, data, labels in (
        (ax1, order, periods, order),
        (ax2, list(energy_names), energies, list(energy_names.values())),
    ):
        values = [data[k]["within1"] * 100 for k in keys]
        colors = [ACCENT if v >= 90 else MUTED for v in values]
        ax.bar(range(len(keys)), values, color=colors, width=0.7)
        ax.axhline(90, color=WARN, linewidth=1, linestyle="--")
        ax.set_xticks(range(len(keys)), labels, rotation=40, ha="right")
        ax.set_ylim(50, 100)
        ax.yaxis.grid(True, color=GRID)
        ax.set_axisbelow(True)
        for x, v in enumerate(values):
            ax.text(x, v + 0.8, fr(v, 0), ha="center", fontsize=8, color=INK)
    ax1.set_ylabel("Accord à ±1 classe (%)")
    ax1.set_title("Par époque de construction", fontsize=10, loc="left")
    ax2.set_title("Par énergie de chauffage", fontsize=10, loc="left")
    ax1.text(-0.4, 91, "critère 90 %", ha="left", fontsize=8, color=WARN)
    save(fig, name)


def by_version(bias: dict, name: str) -> None:
    """Mean Cep bias by DPE method version, calibration vs independent test."""
    versions = ["1", "1.1", "2", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6"]
    series = (
        ("dpe_sample_v2", "Calibration", MUTED, -0.2),
        ("dpe_test_v1", "Test indépendant", ACCENT, 0.2),
    )
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    for key, label, color, offset in series:
        data = bias[key]["by_version"]
        xs = [i + offset for i, v in enumerate(versions) if v in data]
        ys = [data[v]["cep_bias_kwhep_m2"] for v in versions if v in data]
        ax.bar(xs, ys, width=0.38, color=color, label=label)
    ax.axhline(0, color=INK, linewidth=0.8)
    ax.set_xticks(range(len(versions)), [f"v{v}" for v in versions])
    ax.set_xlabel("Version de la méthode DPE (champ version_dpe)")
    ax.set_ylabel("Biais moyen Cep (kWhep/m²/an)")
    ax.yaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.42, 1.0))
    test = bias["dpe_test_v1"]["by_version"]["2.6"]
    ax.annotate(
        f"v2.6 (2026) : biais {fr(test['cep_bias_kwhep_m2'])},\n"
        f"±1 classe {fr(test['within1'] * 100)} % (n = {test['n']})",
        xy=(8.2, test["cep_bias_kwhep_m2"]),
        xytext=(6.1, 62),
        fontsize=8.5,
        color=INK,
        arrowprops={"arrowstyle": "-", "color": MUTED},
    )
    save(fig, name)


def iterations(name: str) -> None:
    """Calibration history then independent test (note de validation §4)."""
    # Iterations 1-5 predate the result files: values copied from the note §4 table.
    steps = [
        ("1", 0.621, 0.274, "cal"),
        ("2", 0.829, 0.421, "cal"),
        ("3", 0.841, 0.427, "cal"),
        ("4", 0.887, 0.481, "cal"),
        ("5", 0.903, 0.502, "cal"),
    ]
    for label, file, kind in (
        ("6 (v1)", "results_v1.json", "cal"),
        ("v2", "results_v2_aux.json", "cal"),
        ("v3", "results_v3_inertia.json", "cal"),
        ("v4", "results_v4_cooling.json", "cal"),
        ("v5", "results_v5_test.json", "test"),
        ("v6", "results_v6_test.json", "test"),
    ):
        r = load(file)
        steps.append((label, r["label_within_one_class"], r["label_exact_agreement"], kind))
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    xs = range(len(steps))
    ax.plot(xs, [s[1] * 100 for s in steps], color=ACCENT, marker="o", label="±1 classe")
    ax.plot(xs, [s[2] * 100 for s in steps], color=MUTED, marker="o", label="Exact")
    ax.axhline(90, color=WARN, linewidth=1, linestyle="--")
    ax.axhline(60, color=WARN, linewidth=1, linestyle=":")
    first_test = next(i for i, s in enumerate(steps) if s[3] == "test")
    ax.axvspan(first_test - 0.5, len(steps) - 0.5, color=GRID, zorder=0)
    ax.text(first_test - 0.4, 95, "échantillon test", fontsize=8.5, color=INK)
    ax.text(0, 91.5, "critère ±1 : 90 %", fontsize=8, color=WARN)
    ax.text(0.3, 61.5, "critère exact : 60 %", fontsize=8, color=WARN)
    ax.set_xticks(list(xs), [s[0] for s in steps])
    ax.set_xlabel("Itération")
    ax.set_ylabel("Accord d'étiquette (%)")
    ax.set_ylim(20, 100)
    ax.yaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower center", ncol=2, bbox_to_anchor=(0.45, 0.0))
    save(fig, name)


def main() -> None:
    test = load("results_v6_test.json")
    confusion(test, "confusion_test_v6.svg", "Test indépendant, campagne v6 (n = 11 496)")
    by_stratum(test, "within1_by_stratum_test_v6.svg")
    by_version(load("bias_analysis_v6.json"), "bias_by_method_version_v6.svg")
    iterations("iterations.svg")


if __name__ == "__main__":
    main()

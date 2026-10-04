"""
Ellingham diagram for metals found in waste printed circuit boards (WPCB).

Reads standard Gibbs energies of oxide formation (per mol O2) calculated with
FactSage (Reaction module, FactPS database), then:
  1. plots the Ellingham diagram (dG vs. temperature),
  2. converts dG into the equilibrium oxygen partial pressure,
  3. prints the stability ranking at a chosen process temperature.

Usage:
    python analysis/plot_ellingham.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "dG_oxidation_FactPS.csv"
FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(exist_ok=True)

R = 8.314                 # gas constant, J/(mol K)
PROCESS_T_C = 800         # temperature used for the ranking table

COLORS = {"Fe": "#7f7f7f", "Sn": "#1f4e79", "Ni": "#2e8b57",
          "Pb": "#8e44ad", "Cu": "#b87333", "Ag": "#c0504d"}


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE)
    df["dG_kJ"] = df["dG_J_per_mol_O2"] / 1000
    df["T_K"] = df["T_C"] + 273.15
    # For M + O2 = MO2-type reactions between pure condensed phases,
    # K = 1 / p(O2), and dG = -RT ln K  ->  log10 p(O2) = dG / (R T ln 10)
    df["log10_pO2_atm"] = df["dG_J_per_mol_O2"] / (R * df["T_K"] * np.log(10))
    return df


def plot_ellingham(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(11, 6))

    # order the legend from most to least stable oxide
    order = (df[df["T_C"] == PROCESS_T_C]
             .sort_values("dG_kJ")["metal"].tolist())

    for metal in order:
        d = df[df["metal"] == metal].sort_values("T_C")
        ax.plot(d["T_C"], d["dG_kJ"], "-", lw=2, color=COLORS[metal],
                label=d["reaction"].iloc[0])
        # mark phase changes (the "blue rows" in FactSage)
        pc = d[d["phase_change"].notna()]
        ax.plot(pc["T_C"], pc["dG_kJ"], "o", ms=6, mfc="white",
                mec=COLORS[metal], mew=1.5)
        # label at the right end of each line
        last = d.iloc[-1]
        ax.text(last["T_C"] + 15, last["dG_kJ"], metal, va="center",
                fontsize=10, fontweight="bold", color=COLORS[metal])

    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(PROCESS_T_C, color="grey", ls=":", lw=1)
    ax.text(PROCESS_T_C + 8, 135, f"{PROCESS_T_C} °C", fontsize=8, color="grey")
    ax.text(510, 12, "oxide unstable (above 0)", fontsize=8, color="grey")
    ax.text(510, -470, "more stable oxide (lower line)", fontsize=8, color="grey")

    ax.set_xlim(500, 1560)
    ax.set_ylim(-480, 150)
    ax.set_xlabel("Temperature (°C)")
    ax.set_ylabel("ΔG° (kJ per mol O$_2$)")
    ax.set_title("Ellingham diagram: metals in waste printed circuit boards\n"
                 "FactSage 8.4 (FactPS), standard states", fontsize=11)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8,
              title="Reaction (○ = phase change)", title_fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "ellingham_diagram.png", dpi=200)
    plt.close(fig)


def ranking_table(df: pd.DataFrame) -> pd.DataFrame:
    t = df[df["T_C"] == PROCESS_T_C].sort_values("dG_kJ")
    t = t[["metal", "reaction", "dG_kJ", "log10_pO2_atm"]].reset_index(drop=True)
    t.index += 1
    return t


def main() -> None:
    df = load_data()
    plot_ellingham(df)

    table = ranking_table(df)
    print(f"Oxide stability ranking at {PROCESS_T_C} °C "
          "(1 = oxidises first)\n")
    print(table.to_string(float_format=lambda v: f"{v:8.1f}"))
    print("\nlog10 p(O2): oxygen pressure (atm) at which metal and oxide "
          "are in equilibrium. Above it the metal oxidises, below it the "
          "oxide is reduced.")
    print(f"\nFigure saved to {FIG_DIR / 'ellingham_diagram.png'}")


if __name__ == "__main__":
    main()

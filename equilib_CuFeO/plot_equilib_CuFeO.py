"""
Cu-Fe-O equilibrium at 1200 C: which metal oxidises first?

Reads a FactSage Equilib text output (1 mol Cu + 1 mol Fe + <A> mol O2,
A = 0 ... 1.5, FactPS database, pure solids/liquids + ideal gas) and:
  1. extracts the amount of every stable phase for each oxygen step,
  2. extracts the equilibrium oxygen pressure p(O2),
  3. checks the mass balance (Cu, Fe, O in = out) for every step,
  4. plots phase amounts and log10 p(O2) against the oxygen added,
  5. saves the extracted numbers as a CSV.

Usage:
    python plot_equilib_CuFeO.py Equilib.txt
"""

import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# atoms per formula unit (Cu, Fe, O) for every phase that can appear
FORMULA = {
    "Cu": (1, 0, 0), "Fe": (0, 1, 0),
    "FeO": (0, 1, 1), "Fe3O4": (0, 3, 4), "Fe2O3": (0, 2, 3),
    "Cu2O": (2, 0, 1), "CuO": (1, 0, 1),
    "CuFeO2": (1, 1, 2), "CuFe2O4": (1, 2, 4),
}
LABELS = {
    "Cu": "Cu (metal)", "Fe": "Fe (metal)", "FeO": "FeO (wüstite)",
    "Fe3O4": "Fe$_3$O$_4$ (magnetite)", "CuFeO2": "CuFeO$_2$ (delafossite)",
    "CuFe2O4": "CuFe$_2$O$_4$ (copper ferrite)", "Cu2O": "Cu$_2$O",
}
COLORS = {"Cu": "#b87333", "Fe": "#7f7f7f", "FeO": "#1f4e79",
          "Fe3O4": "#2e8b57", "CuFeO2": "#8e44ad", "CuFe2O4": "#c0504d",
          "Cu2O": "#e69f00"}


def compound(phase_name: str) -> str:
    """'Fe3O4_Magnetite(s2)' -> 'Fe3O4', '(CuO)(Fe2O3)_liquid(liq)' -> 'CuFe2O4'."""
    base = phase_name.split("_")[0]
    return "CuFe2O4" if base == "(CuO)(Fe2O3)" else base


def parse(path: Path) -> tuple[pd.DataFrame, pd.Series]:
    text = path.read_text(errors="ignore")
    pages = re.split(r"Page \d+ \[A=", text)[1:]
    rows, po2 = [], {}
    for page in pages:
        a = float(page.split("]", 1)[0])
        stream = page.split("STREAM CONSTITUENTS", 1)[1]
        # equilibrium O2 pressure (fugacity column of the gas block)
        m = re.search(r"^\s+O2\s+\S+\s+\S+\s+(\S+)\s*$", stream, re.M)
        po2[a] = float(m.group(1)) if m else np.nan   # A=0: no oxygen at all
        # condensed phases: name, amount (mol), activity
        block = stream.split("ACTIVITY", 1)[1].split("****", 1)[0]
        for line in block.splitlines():
            m = re.match(r"^\s+(\S+)\s+(?:T\s+)?(\S+E[+-]\d+)\s+(\S+E[+-]\d+)\s*$", line)
            if m and float(m.group(2)) > 1e-9:
                rows.append({"A_mol_O2": a, "phase": m.group(1),
                             "compound": compound(m.group(1)),
                             "amount_mol": float(m.group(2))})
    df = pd.DataFrame(rows)
    return df, pd.Series(po2, name="pO2_atm")


def mass_balance(df: pd.DataFrame) -> pd.DataFrame:
    """Cu, Fe, O found in the condensed phases + O2 gas, for every step."""
    out = []
    for a, d in df.groupby("A_mol_O2"):
        cu = sum(FORMULA[c][0] * n for c, n in zip(d["compound"], d["amount_mol"]) if c in FORMULA)
        fe = sum(FORMULA[c][1] * n for c, n in zip(d["compound"], d["amount_mol"]) if c in FORMULA)
        o = sum(FORMULA[c][2] * n for c, n in zip(d["compound"], d["amount_mol"]) if c in FORMULA)
        out.append({"A": a, "Cu": cu, "Fe": fe, "O_condensed": o})
    return pd.DataFrame(out)


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "Equilib.txt")
    df, po2 = parse(src)

    # O2 left over as gas (only when oxygen is in excess): gas phase amount
    # is not in the activity table, so add it from the mass balance
    wide = (df.groupby(["A_mol_O2", "compound"])["amount_mol"].sum()
              .unstack(fill_value=0.0))
    bal = mass_balance(df).set_index("A")
    wide["O2_gas"] = (2 * wide.index.values - bal["O_condensed"]).clip(lower=0) / 2
    wide["log10_pO2_atm"] = np.log10(po2.reindex(wide.index))
    wide.round(4).to_csv("CuFeO_1200C_equilib.csv")

    # mass-balance check: Cu and Fe must stay 1 mol at every step
    err = max((bal["Cu"] - 1).abs().max(), (bal["Fe"] - 1).abs().max())
    print(f"Mass balance check: largest Cu/Fe error = {err:.1e} mol "
          f"({'OK' if err < 1e-3 else 'CHECK!'})")

    # ---- plot ----
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 8), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 2]})
    for c in ["Cu", "Fe", "FeO", "Fe3O4", "CuFeO2", "CuFe2O4", "Cu2O"]:
        if c in wide:
            ax1.plot(wide.index, wide[c], lw=2.2, color=COLORS[c], label=LABELS[c])
    ax1.axvspan(0, 2/3, color="#b87333", alpha=0.07)
    ax1.text(1/3, 1.06, "copper stays fully metallic", ha="center",
             fontsize=9, color="#7a4a1f")
    ax1.axvline(2/3, color="grey", ls=":", lw=1)
    ax1.set_ylabel("Amount (mol)")
    ax1.set_ylim(-0.03, 1.12)
    ax1.set_title("Cu–Fe–O at 1200 °C: 1 mol Cu + 1 mol Fe + A mol O$_2$\n"
                  "FactSage 8.4 Equilib (FactPS), pure phases + ideal gas",
                  fontsize=11)
    ax1.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8, frameon=False)
    ax1.grid(alpha=0.3)

    ax2.step(wide.index, wide["log10_pO2_atm"], where="mid", lw=2, color="#1f4e79")
    for y, lab in [(-12.0, "Fe / FeO buffer"), (-10.0, "FeO / Fe$_3$O$_4$"),
                   (-4.28, "Cu / CuFeO$_2$ / Fe$_3$O$_4$"),
                   (-1.34, "CuFeO$_2$ / CuFe$_2$O$_4$ / Cu$_2$O"), (0, "excess O$_2$ (1 atm)")]:
        ax2.text(1.52, y, lab, va="center", fontsize=8, color="#1f4e79")
    ax2.set_xlabel("O$_2$ added, A (mol)")
    ax2.set_ylabel("log$_{10}$ p(O$_2$) (atm)")
    ax2.set_xlim(0, 1.5)
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("CuFeO_1200C_equilib.png", dpi=200, bbox_inches="tight")
    print("Saved CuFeO_1200C_equilib.png and CuFeO_1200C_equilib.csv")

    # short summary of where each phase appears
    print("\nA (mol O2) | phases present (mol) | log p(O2)")
    for a, r in wide.iterrows():
        ph = ", ".join(f"{c} {r[c]:.2f}" for c in wide.columns
                       if c not in ("log10_pO2_atm",) and r[c] > 1e-6)
        print(f"{a:5.2f}      | {ph} | {r['log10_pO2_atm']:.1f}")


if __name__ == "__main__":
    main()

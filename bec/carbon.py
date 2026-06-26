"""Embodied carbon (A1-A3 product stage) calculations.

Carbon intensity rates are hardcoded from Finnish precast industry EPD
data (EN 15804, A1-A3: raw material extraction, transport to factory,
and manufacturing only -- installation, transport to site, and
end-of-life are excluded). Areas and quantities are read straight from
the same schedule rows and area formula already used in bec.bom (slabs:
plan area; walls/sandwich/lift shaft: face area = length x storey
height) -- nothing here recomputes geometry.
"""

from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from bec.bom import _element_area_m2
from bec.constants import (
    CROSSWALL_CODE,
    LIFT_SHAFT_CODE,
    SANDWICH_CODE,
    SLAB_CODE_LONG,
    SLAB_CODE_SHORT,
    STAIR_FLIGHT_CODE,
    STAIR_LANDING_CODE,
)
from bec.model import BuildingGeom
from bec.schedule import build_element_schedule_rows
from bec.summary import total_gfa_m2

CARBON_COLUMNS = [
    "Element Type", "BEC Code", "Area or Qty",
    "Carbon Rate (kgCO2e/unit)", "Total Carbon (kgCO2e)", "% of Total",
]

# kgCO2e per m2 of element area (slabs: plan area; walls/sandwich/lift
# shaft: face area), per Finnish precast EPD data (EN 15804, A1-A3).
CARBON_AREA_RATES = {
    SLAB_CODE_SHORT: 58,
    SLAB_CODE_LONG: 71,
    CROSSWALL_CODE: 63,
    SANDWICH_CODE: 66,
    LIFT_SHAFT_CODE: 81,
}

# kgCO2e per piece -- stair elements aren't priced by area, same as bec.bom.
CARBON_EACH_RATES = {
    STAIR_FLIGHT_CODE: 546,
    STAIR_LANDING_CODE: 111,
}

BENCHMARK_AMBER_THRESHOLD = 1.2  # >20% above benchmark = red, up to 20% above = amber


def _scale_benchmark(building: BuildingGeom) -> float:
    """Return the applicable kgCO₂e/m² GFA benchmark based on building scale.

    Larger buildings have lower wall-to-floor ratios and therefore lower
    carbon intensities per m² GFA; smaller buildings are penalised by geometry,
    not by system inefficiency.
    """
    scale = building.num_units * building.num_storeys
    if scale >= 8:
        return 120.0
    elif scale >= 4:
        return 150.0
    return 180.0


def build_carbon_rows(building: BuildingGeom, storey_height_mm: int) -> List[Dict[str, Any]]:
    totals: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for r in build_element_schedule_rows(building):
        code = r["BEC Code"]
        qty = r["Total Qty (all floors)"]
        key = (r["Element Type"], code)
        entry = totals.setdefault(key, {"area_or_qty": 0.0, "carbon": 0.0, "unit": "", "rate": 0})

        if code in CARBON_EACH_RATES:
            rate = CARBON_EACH_RATES[code]
            entry["area_or_qty"] += qty
            entry["carbon"] += rate * qty
            entry["unit"] = "pcs"
        else:
            rate = CARBON_AREA_RATES[code]
            total_area = _element_area_m2(r, storey_height_mm) * qty
            entry["area_or_qty"] += total_area
            entry["carbon"] += rate * total_area
            entry["unit"] = "m²"
        entry["rate"] = rate

    grand_total = sum(e["carbon"] for e in totals.values())

    rows: List[Dict[str, Any]] = []
    for (element_type, code), entry in totals.items():
        pct = (entry["carbon"] / grand_total * 100) if grand_total else 0.0
        qty_label = (
            f"{entry['area_or_qty']:.1f} m²" if entry["unit"] == "m²"
            else f"{int(entry['area_or_qty'])} pcs"
        )
        rows.append({
            "Element Type": element_type,
            "BEC Code": code,
            "Area or Qty": qty_label,
            "Carbon Rate (kgCO2e/unit)": entry["rate"],
            "Total Carbon (kgCO2e)": round(entry["carbon"], 1),
            "% of Total": round(pct, 1),
        })

    rows.sort(key=lambda row: row["Total Carbon (kgCO2e)"], reverse=True)
    return rows


def build_carbon_df(building: BuildingGeom, storey_height_mm: int) -> pd.DataFrame:
    rows = build_carbon_rows(building, storey_height_mm)
    df = pd.DataFrame(rows, columns=CARBON_COLUMNS)
    total_row = {
        "Element Type": "TOTAL",
        "BEC Code": "",
        "Area or Qty": "",
        "Carbon Rate (kgCO2e/unit)": "",
        "Total Carbon (kgCO2e)": round(df["Total Carbon (kgCO2e)"].sum(), 1),
        "% of Total": round(df["% of Total"].sum(), 1),
    }
    return pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)


def carbon_summary(rows: List[Dict[str, Any]], building: BuildingGeom) -> Dict[str, Any]:
    total_carbon_kg = sum(r["Total Carbon (kgCO2e)"] for r in rows)
    gfa_m2 = total_gfa_m2(building)
    intensity = (total_carbon_kg / gfa_m2) if gfa_m2 else 0.0

    heaviest = max(rows, key=lambda r: r["Total Carbon (kgCO2e)"]) if rows else None

    benchmark = _scale_benchmark(building)
    ratio = (intensity / benchmark) if benchmark else 0.0
    if ratio <= 1.0:
        benchmark_status = "green"
    elif ratio <= BENCHMARK_AMBER_THRESHOLD:
        benchmark_status = "amber"
    else:
        benchmark_status = "red"

    return {
        "total_carbon_tonnes": total_carbon_kg / 1000,
        "intensity_kg_m2_gfa": intensity,
        "heaviest_type": heaviest["Element Type"] if heaviest else "—",
        "heaviest_pct": heaviest["% of Total"] if heaviest else 0.0,
        "benchmark_kg_m2_gfa": benchmark,
        "benchmark_status": benchmark_status,
    }


def render_carbon_chart(rows: List[Dict[str, Any]]) -> Figure:
    sorted_rows = sorted(rows, key=lambda r: r["Total Carbon (kgCO2e)"])
    labels = [f"{r['Element Type']} ({r['BEC Code']})" for r in sorted_rows]
    values = [r["Total Carbon (kgCO2e)"] for r in sorted_rows]

    fig_h = max(3.0, 0.6 * len(sorted_rows) + 1.0)
    fig, ax = plt.subplots(figsize=(9, fig_h))
    bars = ax.barh(labels, values, color="#5b9bd5")
    max_val = max(values) if values else 1
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_width() + max_val * 0.01, bar.get_y() + bar.get_height() / 2,
            f"{value:,.0f} kgCO₂e", va="center", fontsize=8,
        )

    ax.set_xlabel("kgCO₂e")
    ax.set_title("Embodied Carbon by Element Type (kgCO₂e, A1–A3)", fontsize=11, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def render_benchmark_bar(intensity_kg_m2: float, benchmark_kg_m2: float, status: str) -> Figure:
    color_map = {"green": "#2e7d32", "amber": "#f0b429", "red": "#c62828"}
    labels = ["This building", "Finnish benchmark"]
    values = [intensity_kg_m2, benchmark_kg_m2]
    colors = [color_map[status], "#9e9e9e"]

    fig, ax = plt.subplots(figsize=(8, 1.8))
    bars = ax.barh(labels, values, color=colors, height=0.5)
    max_val = max(values) if max(values) > 0 else 1
    for bar, value in zip(bars, values):
        ax.text(bar.get_width() + max_val * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{value:.0f}", va="center", fontsize=9)
    ax.set_xlabel("kgCO₂e / m² GFA")
    ax.set_xlim(0, max_val * 1.2)
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig

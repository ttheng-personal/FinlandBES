"""Bill of Materials calculations.

All quantities and dimensions are read straight from
bec.schedule.build_element_schedule_rows(), which itself reads off the
existing BuildingGeom -- nothing here recomputes building geometry.

Wall/sandwich rates apply to wall FACE area (length x height); slab
rates apply to plan area (a slab is a horizontal element, no height
needed). The storey height used for that face-area calculation is a
sidebar input (see app.py) passed in as storey_height_mm -- it has no
effect on plan geometry or any other tab.
"""

from typing import Any, Dict, List

import pandas as pd

from bec.constants import (
    BEC_ELEMENT_TERMS,
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

BOM_COLUMNS = [
    "Element Type", "BEC Code", "Finnish Term", "English Description",
    "Unit Dimensions (mm)", "Unit Weight (kg)",
    "Quantity", "Total Weight (tonnes)", "Concrete Volume (m³)",
    "Reinforcement Steel (kg)", "Insulation Area (m²)", "Unit Cost (EUR)", "Total Cost (EUR)",
]

# Rates per m2 of element area (slabs: plan area; walls/sandwich: face area).
AREA_RATES = {
    SLAB_CODE_SHORT: dict(kg_m2=285, conc_m3_m2=0.153, steel_kg_m2=18, insul_m2_m2=0.0, cost_eur_m2=38),
    SLAB_CODE_LONG: dict(kg_m2=370, conc_m3_m2=0.185, steel_kg_m2=22, insul_m2_m2=0.0, cost_eur_m2=44),
    CROSSWALL_CODE: dict(kg_m2=360, conc_m3_m2=0.150, steel_kg_m2=25, insul_m2_m2=0.0, cost_eur_m2=75),
    SANDWICH_CODE: dict(kg_m2=390, conc_m3_m2=0.160, steel_kg_m2=16, insul_m2_m2=1.0, cost_eur_m2=210),
    LIFT_SHAFT_CODE: dict(kg_m2=480, conc_m3_m2=0.200, steel_kg_m2=30, insul_m2_m2=0.0, cost_eur_m2=120),
}

# Fixed per-piece rates (stair elements aren't priced by area).
EACH_RATES = {
    STAIR_FLIGHT_CODE: dict(kg_each=3500, conc_m3_each=1.4, steel_kg_each=180, cost_eur_each=3200),
    STAIR_LANDING_CODE: dict(kg_each=700, conc_m3_each=0.29, steel_kg_each=35, cost_eur_each=650),
}


def _element_area_m2(row: Dict[str, Any], storey_height_mm: int) -> float:
    code = row["BEC Code"]
    if code in (SLAB_CODE_SHORT, SLAB_CODE_LONG):
        return (row["_dim_a_mm"] / 1000) * (row["_dim_b_mm"] / 1000)
    length_mm = row["_dim_b_mm"]
    return (length_mm / 1000) * (storey_height_mm / 1000)


def build_bom_rows(building: BuildingGeom, storey_height_mm: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for r in build_element_schedule_rows(building):
        code = r["BEC Code"]
        qty = r["Total Qty (all floors)"]
        finnish_term, english_desc = BEC_ELEMENT_TERMS[code]

        if code in EACH_RATES:
            rate = EACH_RATES[code]
            unit_weight = rate["kg_each"]
            unit_conc = rate["conc_m3_each"]
            unit_steel = rate["steel_kg_each"]
            unit_insul = 0.0
            unit_cost = rate["cost_eur_each"]
        else:
            rate = AREA_RATES[code]
            area = _element_area_m2(r, storey_height_mm)
            unit_weight = rate["kg_m2"] * area
            unit_conc = rate["conc_m3_m2"] * area
            unit_steel = rate["steel_kg_m2"] * area
            unit_insul = rate["insul_m2_m2"] * area
            unit_cost = rate["cost_eur_m2"] * area

        rows.append({
            "Element Type": r["Element Type"],
            "BEC Code": code,
            "Finnish Term": finnish_term,
            "English Description": english_desc,
            "Unit Dimensions (mm)": r["Unit Dimensions (mm)"],
            "Unit Weight (kg)": round(unit_weight, 1),
            "Quantity": qty,
            "Total Weight (tonnes)": round(unit_weight * qty / 1000, 2),
            "Concrete Volume (m³)": round(unit_conc * qty, 2),
            "Reinforcement Steel (kg)": round(unit_steel * qty, 1),
            "Insulation Area (m²)": round(unit_insul * qty, 1),
            "Unit Cost (EUR)": round(unit_cost, 0),
            "Total Cost (EUR)": round(unit_cost * qty, 0),
        })
    return rows


def build_bom_df(building: BuildingGeom, storey_height_mm: int) -> pd.DataFrame:
    rows = build_bom_rows(building, storey_height_mm)
    df = pd.DataFrame(rows, columns=BOM_COLUMNS)
    return df


def build_bom_summary(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "Element Type": "TOTAL",
        "BEC Code": "",
        "Finnish Term": "",
        "English Description": "",
        "Unit Dimensions (mm)": "",
        "Unit Weight (kg)": "",
        "Quantity": int(df["Quantity"].sum()),
        "Total Weight (tonnes)": round(df["Total Weight (tonnes)"].sum(), 2),
        "Concrete Volume (m³)": round(df["Concrete Volume (m³)"].sum(), 2),
        "Reinforcement Steel (kg)": round(df["Reinforcement Steel (kg)"].sum(), 1),
        "Insulation Area (m²)": round(df["Insulation Area (m²)"].sum(), 1),
        "Unit Cost (EUR)": "",
        "Total Cost (EUR)": round(df["Total Cost (EUR)"].sum(), 0),
    }


def build_bom_df_with_total(building: BuildingGeom, storey_height_mm: int) -> pd.DataFrame:
    df = build_bom_df(building, storey_height_mm)
    summary = build_bom_summary(df)
    return pd.concat([df, pd.DataFrame([summary])], ignore_index=True)

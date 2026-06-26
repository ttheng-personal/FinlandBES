"""Element schedule extraction.

Every count and dimension here is read directly off the BuildingGeom
produced by bec.model.build_building() -- no positions or lengths are
recomputed, only grouped/summed.

Slab code rule: unit width <= 6 bays (7,200mm) -> O27, otherwise O32.
"""

from collections import OrderedDict
from typing import Any, Dict, List

import pandas as pd

from bec.constants import (
    BAY_MM,
    BEC_ELEMENT_TERMS,
    CROSSWALL_CODE,
    LIFT_SHAFT_CODE,
    LIFT_SHAFT_THICKNESS_MM,
    SANDWICH_CODE,
    SLAB_CODE_LONG,
    SLAB_CODE_SHORT,
    SLAB_SPAN_THRESHOLD_MM,
    STAIR_FLIGHT_CODE,
    STAIR_LANDING_CODE,
)
from bec.model import BuildingGeom

# Stair flight/landing plan dimensions aren't tracked as geometry in
# BuildingGeom (only the stair shaft footprint is) -- these are fixed,
# grid-aligned reference dimensions for the schedule.
STAIR_FLIGHT_DIMENSIONS_MM = (BAY_MM, 2 * BAY_MM)   # 1200 x 2400
STAIR_LANDING_DIMENSIONS_MM = (BAY_MM, BAY_MM)      # 1200 x 1200

# Standard half-turn precast stair: 2 flights + 1 intermediate landing
# per inter-storey rise. There are (num_storeys - 1) rises in a building.
STAIR_FLIGHTS_PER_RISE = 2
STAIR_LANDINGS_PER_RISE = 1

# Lift shaft perimeter: a 1200 x 2400mm rectangle has 2 short (1200mm)
# sides and 2 long (2400mm) sides, repeated once per storey (unlike
# stairs, the shaft wall exists at every floor level, not just rises).
LIFT_SHAFT_SHORT_PANELS = 2
LIFT_SHAFT_LONG_PANELS = 2

SCHEDULE_COLUMNS = [
    "Element Type", "BEC Code", "Finnish Term", "English Description",
    "Unit Dimensions (mm)", "Qty per Floor", "Total Qty (all floors)",
]


def _slab_code(unit_width_mm: int) -> str:
    return SLAB_CODE_SHORT if unit_width_mm <= SLAB_SPAN_THRESHOLD_MM else SLAB_CODE_LONG


def _terms(code: str):
    return BEC_ELEMENT_TERMS[code]


def build_element_schedule_rows(building: BuildingGeom) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    # 1. Hollow-core slabs: one schedule line for the building -- every
    # unit shares the same span (unit width) and the standard 1200mm
    # panel module repeated once per bay of unit depth.
    unit_width_mm = building.width_bays * BAY_MM
    panels_per_unit = building.depth_bays
    qty_per_floor = len(building.units) * panels_per_unit
    slab_code = _slab_code(unit_width_mm)
    slab_fi, slab_en = _terms(slab_code)
    rows.append({
        "Element Type": "Hollow-core slab",
        "BEC Code": slab_code,
        "Finnish Term": slab_fi,
        "English Description": slab_en,
        "Unit Dimensions (mm)": f"{BAY_MM} × {unit_width_mm}",
        "Qty per Floor": qty_per_floor,
        "Total Qty (all floors)": qty_per_floor * building.num_storeys,
        "_dim_a_mm": BAY_MM,
        "_dim_b_mm": unit_width_mm,
    })

    # 2. Load-bearing cross-walls, grouped by their modelled length.
    cw_fi, cw_en = _terms(CROSSWALL_CODE)
    cw_groups: "OrderedDict[int, int]" = OrderedDict()
    for wall in building.cross_walls:
        length = wall.rect.depth  # cross-walls run along the depth axis
        cw_groups[length] = cw_groups.get(length, 0) + 1
    for length, count in sorted(cw_groups.items(), reverse=True):
        rows.append({
            "Element Type": "Load-bearing cross-wall",
            "BEC Code": CROSSWALL_CODE,
            "Finnish Term": cw_fi,
            "English Description": cw_en,
            "Unit Dimensions (mm)": f"150 × {length}",
            "Qty per Floor": count,
            "Total Qty (all floors)": count * building.num_storeys,
            "_dim_a_mm": 150,
            "_dim_b_mm": length,
        })

    # 3. Sandwich panels, grouped by their modelled length.
    sw_fi, sw_en = _terms(SANDWICH_CODE)
    sw_groups: "OrderedDict[int, int]" = OrderedDict()
    for wall in building.sandwich_walls:
        length = wall.rect.width  # sandwich panels run along the width axis
        sw_groups[length] = sw_groups.get(length, 0) + 1
    for length, count in sorted(sw_groups.items(), reverse=True):
        rows.append({
            "Element Type": "Sandwich panel (exterior)",
            "BEC Code": SANDWICH_CODE,
            "Finnish Term": sw_fi,
            "English Description": sw_en,
            "Unit Dimensions (mm)": f"360 × {length}",
            "Qty per Floor": count,
            "Total Qty (all floors)": count * building.num_storeys,
            "_dim_a_mm": 360,
            "_dim_b_mm": length,
        })

    # 4 & 5. Stair flights / landings: only present once a stair core
    # exists (num_storeys > 1). Counted per inter-storey rise -- there
    # are (num_storeys - 1) rises, since the top floor needs no further
    # rise.
    if building.stair_core is not None:
        rises = building.num_storeys - 1
        flight_w, flight_l = STAIR_FLIGHT_DIMENSIONS_MM
        flight_fi, flight_en = _terms(STAIR_FLIGHT_CODE)
        rows.append({
            "Element Type": "Stair flight",
            "BEC Code": STAIR_FLIGHT_CODE,
            "Finnish Term": flight_fi,
            "English Description": flight_en,
            "Unit Dimensions (mm)": f"{flight_w} × {flight_l}",
            "Qty per Floor": STAIR_FLIGHTS_PER_RISE,
            "Total Qty (all floors)": STAIR_FLIGHTS_PER_RISE * rises,
            "_dim_a_mm": flight_w,
            "_dim_b_mm": flight_l,
        })
        land_w, land_l = STAIR_LANDING_DIMENSIONS_MM
        land_fi, land_en = _terms(STAIR_LANDING_CODE)
        rows.append({
            "Element Type": "Stair landing",
            "BEC Code": STAIR_LANDING_CODE,
            "Finnish Term": land_fi,
            "English Description": land_en,
            "Unit Dimensions (mm)": f"{land_w} × {land_l}",
            "Qty per Floor": STAIR_LANDINGS_PER_RISE,
            "Total Qty (all floors)": STAIR_LANDINGS_PER_RISE * rises,
            "_dim_a_mm": land_w,
            "_dim_b_mm": land_l,
        })

    # 6. Lift shaft wall panels: only present once a lift shaft exists
    # (num_storeys >= LIFT_SHAFT_TRIGGER_STOREYS). 4 panels enclose the
    # 1200 x 2400mm shaft per storey: 2 short (1200mm wide) + 2 long
    # (2400mm wide), both 200mm thick, full storey height.
    if building.lift_shaft is not None:
        hk_fi, hk_en = _terms(LIFT_SHAFT_CODE)
        for panel_width, qty_per_floor in ((BAY_MM, LIFT_SHAFT_SHORT_PANELS), (2 * BAY_MM, LIFT_SHAFT_LONG_PANELS)):
            rows.append({
                "Element Type": "Lift shaft wall panel",
                "BEC Code": LIFT_SHAFT_CODE,
                "Finnish Term": hk_fi,
                "English Description": hk_en,
                "Unit Dimensions (mm)": f"{LIFT_SHAFT_THICKNESS_MM} × {panel_width}",
                "Qty per Floor": qty_per_floor,
                "Total Qty (all floors)": qty_per_floor * building.num_storeys,
                "_dim_a_mm": LIFT_SHAFT_THICKNESS_MM,
                "_dim_b_mm": panel_width,
            })

    return rows


def build_element_schedule_df(building: BuildingGeom) -> pd.DataFrame:
    rows = build_element_schedule_rows(building)
    df = pd.DataFrame(rows, columns=SCHEDULE_COLUMNS)

    unique_types = df["Element Type"].nunique()
    total_row = {
        "Element Type": f"TOTAL — {unique_types} unique element types",
        "BEC Code": "—",
        "Finnish Term": "—",
        "English Description": "—",
        "Unit Dimensions (mm)": "—",
        "Qty per Floor": int(df["Qty per Floor"].sum()),
        "Total Qty (all floors)": int(df["Total Qty (all floors)"].sum()),
    }
    return pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

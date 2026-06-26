"""Building Summary metrics.

Every figure here is derived from the existing BuildingGeom (bec.model)
and the wall-thickness constants already defined in bec.constants --
no new geometry is computed.

Net area rule: a room loses half the structural wall thickness on any
edge that coincides with the unit's outer boundary (cross-wall on the
left/right, sandwich panel on the front/back). Edges shared with another
room inside the same unit are non-structural partitions and are not
deducted. Because every zone within a unit always spans the full width
between the two bounding cross-walls, and the three depth zones (living
/ kitchen+bathroom / bedrooms) always partition the full unit depth, the
sum of every room's net area always reconciles exactly with the whole
unit's net area computed the same way.
"""

from typing import List, Tuple

from bec.constants import BAY_MM, CROSSWALL_THICKNESS_MM, SANDWICH_THICKNESS_MM
from bec.model import BuildingGeom, Room, UnitGeom

HALF_CROSSWALL_MM = CROSSWALL_THICKNESS_MM / 2
HALF_SANDWICH_MM = SANDWICH_THICKNESS_MM / 2


def _room_net_dims_mm(room: Room, unit: UnitGeom) -> Tuple[float, float]:
    width = float(room.rect.width)
    if room.rect.x0 == unit.rect.x0:
        width -= HALF_CROSSWALL_MM
    if room.rect.x1 == unit.rect.x1:
        width -= HALF_CROSSWALL_MM

    depth = float(room.rect.depth)
    if room.rect.y0 == unit.rect.y0:
        depth -= HALF_SANDWICH_MM
    if room.rect.y1 == unit.rect.y1:
        depth -= HALF_SANDWICH_MM

    return width, depth


def room_net_area_m2(room: Room, unit: UnitGeom) -> float:
    w, d = _room_net_dims_mm(room, unit)
    return (w * d) / 1_000_000


def unit_net_area_m2(unit: UnitGeom) -> float:
    return sum(room_net_area_m2(r, unit) for r in unit.rooms)


def bedroom_rooms(unit: UnitGeom) -> List[Room]:
    return [r for r in unit.rooms if r.kind == "bedroom"]


def room_by_kind(unit: UnitGeom, kind: str) -> Room:
    return next(r for r in unit.rooms if r.kind == kind)


def gross_floor_area_per_storey_m2(building: BuildingGeom) -> float:
    """Gross Floor Area excludes the lift shaft -- it's common circulation
    area, not floor area. The shaft only occupies the front 2 bays of its
    column (see bec.model), so the rest of that column was never real
    floor area either; excluding the whole bay-wide column (not just the
    shaft's own small footprint) keeps GFA accurate rather than counting
    that phantom remainder as usable area.
    """
    effective_width = building.width_mm
    if building.lift_shaft is not None:
        effective_width -= BAY_MM
    return (effective_width * building.depth_mm) / 1_000_000


def total_gfa_m2(building: BuildingGeom) -> float:
    return gross_floor_area_per_storey_m2(building) * building.num_storeys


def total_dwellings(building: BuildingGeom) -> int:
    return building.num_units * building.num_storeys


def arrangement_label(building: BuildingGeom) -> str:
    if building.arrangement == "row":
        return "Row"
    return f"{building.cols}×{building.rows} Grid"

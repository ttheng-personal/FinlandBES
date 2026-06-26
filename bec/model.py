"""Geometry model for the BEC Residential Layout Generator.

Hard rules enforced throughout this module:
  1. Every coordinate is an integer multiple of BAY_MM (1200mm) -- grid lock
     is absolute, no exceptions.
  2. Hollow-core slabs always span between load-bearing cross-walls
     (i.e. across the unit WIDTH), never parallel to them.
  3. Exterior sandwich panels are never load-bearing.

Layout, per unit (front = y0, rear = y1):
  - Living room:        2 bays deep, full width, at the front.
  - Kitchen / Bathroom:  next 2 bays deep, split width (kitchen | bathroom).
  - Bedrooms:            remaining depth, full width split into N bedrooms
                         (3 bay unit -> 1, 4 bay -> 2, 5 bay -> 3).

Building assembly:
  - "row":  units placed side by side along X, 1 row.
  - "grid": 2 columns, N // 2 rows, stacked along Y.
  - Load-bearing cross-walls run the full building depth at every unit
    column boundary (x = c * unit_width for c in 0..cols).
  - Non-load-bearing sandwich panels form the front/rear exterior facades
    (and, between stacked rows in grid arrangement, the internal facades
    of the unit blocks only -- the stair shaft is never interrupted).
  - A single shared stair core (1 bay wide, full building depth) is
    appended to the right-hand edge of the footprint when num_storeys > 1.
  - A lift shaft (1 bay wide x 2 bays deep) is appended immediately
    beside the stair core, on the side away from the units, when
    num_storeys >= LIFT_SHAFT_TRIGGER_STOREYS. Mandatory, no override.
    The building's overall width (used for footprint/GFA/drawing) grows
    by one more bay to fit it; the shaft itself only occupies the front
    2 bays of that column -- the rest of that column beyond the shaft is
    not real floor area (see bec.summary for how GFA accounts for this).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Literal

from bec.constants import (
    BAY_MM,
    CROSSWALL_THICKNESS_MM,
    LIFT_SHAFT_DEPTH_BAYS,
    LIFT_SHAFT_TRIGGER_STOREYS,
    LIFT_SHAFT_WIDTH_BAYS,
    SANDWICH_THICKNESS_MM,
)

Arrangement = Literal["row", "grid"]


@dataclass(frozen=True)
class Rect:
    """A rectangle in plan, in mm.

    Room/unit/stair-core rects sit exactly on the BAY_MM grid (their
    corners ARE grid intersections -- this is the absolute grid lock).
    Wall rects are an exception by construction: a wall is centred ON a
    grid line but drawn with its real physical thickness, so it extends
    a few cm either side of that grid line. The grid lock rule governs
    the structural grid (centrelines / room boundaries), not the applied
    thickness of the elements built on it.
    """

    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def depth(self) -> int:
        return self.y1 - self.y0

    @property
    def area_m2(self) -> float:
        return (self.width / 1000) * (self.depth / 1000)


@dataclass(frozen=True)
class Room:
    rect: Rect
    kind: str   # 'living' | 'kitchen' | 'bathroom' | 'bedroom'
    label: str


@dataclass(frozen=True)
class UnitGeom:
    index: int
    rect: Rect
    rooms: List[Room]
    slab_span_mm: int   # span between the two cross-walls bounding this unit


@dataclass(frozen=True)
class WallSegment:
    rect: Rect
    kind: str            # 'crosswall' | 'sandwich'
    load_bearing: bool


@dataclass(frozen=True)
class StairCore:
    rect: Rect


@dataclass(frozen=True)
class LiftShaft:
    rect: Rect


@dataclass(frozen=True)
class BuildingGeom:
    width_mm: int
    depth_mm: int
    units: List[UnitGeom]
    cross_walls: List[WallSegment]
    sandwich_walls: List[WallSegment]
    stair_core: Optional[StairCore]
    lift_shaft: Optional[LiftShaft]
    num_storeys: int
    num_units: int
    width_bays: int
    depth_bays: int
    arrangement: Arrangement
    rows: int
    cols: int


def _assert_grid_aligned(*values: int) -> None:
    """Hard rule 1: every coordinate on the modular grid must be an
    integer multiple of BAY_MM (1200mm) -- no exceptions."""
    for v in values:
        if v % BAY_MM != 0:
            raise ValueError(f"Coordinate {v}mm is not aligned to the {BAY_MM}mm BEC grid")


def _split_even(total_bays: int, n: int) -> List[int]:
    """Split total_bays whole bays into n integer parts, as equal as
    possible. Every part stays on the 1200mm grid -- no fractional bays."""
    base, rem = divmod(total_bays, n)
    return [base + 1 if i < rem else base for i in range(n)]


def _bedroom_count(width_bays: int) -> int:
    return {3: 1, 4: 2, 5: 3}[width_bays]


def _build_unit_rooms(width_bays: int, depth_bays: int) -> List[Room]:
    w_mm = width_bays * BAY_MM
    rooms: List[Room] = []

    # Living room: 2 bays deep, full width, at the front (y = 0)
    living_depth = 2 * BAY_MM
    rooms.append(Room(Rect(0, 0, w_mm, living_depth), "living", "Living Room"))

    # Kitchen / Bathroom: next 2 bays deep, split width
    kb_y0 = living_depth
    kb_y1 = kb_y0 + 2 * BAY_MM
    kitchen_bays, bathroom_bays = _split_even(width_bays, 2)
    kitchen_w = kitchen_bays * BAY_MM
    rooms.append(Room(Rect(0, kb_y0, kitchen_w, kb_y1), "kitchen", "Kitchen"))
    rooms.append(Room(Rect(kitchen_w, kb_y0, w_mm, kb_y1), "bathroom", "Bathroom"))

    # Bedrooms: remaining depth, full width split by count
    bed_y0 = kb_y1
    bed_y1 = depth_bays * BAY_MM
    bed_count = _bedroom_count(width_bays)
    bed_split = _split_even(width_bays, bed_count)
    x = 0
    for i, bays in enumerate(bed_split):
        bw = bays * BAY_MM
        label = "Bedroom" if bed_count == 1 else f"Bedroom {i + 1}"
        rooms.append(Room(Rect(x, bed_y0, x + bw, bed_y1), "bedroom", label))
        x += bw

    for rm in rooms:
        _assert_grid_aligned(rm.rect.x0, rm.rect.y0, rm.rect.x1, rm.rect.y1)

    return rooms


def build_building(
    num_units: int,
    num_storeys: int,
    width_bays: int,
    depth_bays: int,
    arrangement: Arrangement,
) -> BuildingGeom:
    if arrangement == "grid" and num_units not in (4, 6):
        raise ValueError("Grid arrangement is only valid for 4 or 6 units")

    unit_w = width_bays * BAY_MM
    unit_d = depth_bays * BAY_MM

    if arrangement == "grid":
        cols = 2
        rows = num_units // cols
    else:
        cols = num_units
        rows = 1

    units: List[UnitGeom] = []
    idx = 1
    for r in range(rows):
        for c in range(cols):
            ux0 = c * unit_w
            uy0 = r * unit_d
            local_rooms = _build_unit_rooms(width_bays, depth_bays)
            placed_rooms = [
                Room(
                    Rect(ux0 + rm.rect.x0, uy0 + rm.rect.y0, ux0 + rm.rect.x1, uy0 + rm.rect.y1),
                    rm.kind,
                    rm.label,
                )
                for rm in local_rooms
            ]
            _assert_grid_aligned(ux0, uy0, ux0 + unit_w, uy0 + unit_d)
            units.append(UnitGeom(idx, Rect(ux0, uy0, ux0 + unit_w, uy0 + unit_d), placed_rooms, unit_w))
            idx += 1

    arrangement_width = cols * unit_w
    arrangement_depth = rows * unit_d

    has_stair = num_storeys > 1
    total_width = arrangement_width
    stair_core = None
    if has_stair:
        _assert_grid_aligned(arrangement_width, arrangement_width + BAY_MM, arrangement_depth)
        stair_core = StairCore(Rect(arrangement_width, 0, arrangement_width + BAY_MM, arrangement_depth))
        total_width = arrangement_width + BAY_MM

    # Lift shaft: mandatory, no user override, once storeys reach the
    # trigger. Sits immediately beside the stair core, on the side away
    # from the units -- i.e. appended to whatever the current right edge
    # (total_width) is. Only 2 bays deep (not full building depth).
    lift_shaft = None
    if has_stair and num_storeys >= LIFT_SHAFT_TRIGGER_STOREYS:
        ls_w = LIFT_SHAFT_WIDTH_BAYS * BAY_MM
        ls_d = LIFT_SHAFT_DEPTH_BAYS * BAY_MM
        ls_x0 = total_width
        _assert_grid_aligned(ls_x0, ls_x0 + ls_w, ls_d)
        lift_shaft = LiftShaft(Rect(ls_x0, 0, ls_x0 + ls_w, ls_d))
        total_width = ls_x0 + ls_w

    total_depth = arrangement_depth

    # Load-bearing cross-walls: one continuous wall per column boundary,
    # running the full building depth. Slabs (within each unit) span
    # WIDTH-wise between these -- perpendicular to them, never parallel.
    half_cw = CROSSWALL_THICKNESS_MM // 2
    cross_walls: List[WallSegment] = []
    for c in range(cols + 1):
        x = c * unit_w
        cross_walls.append(
            WallSegment(Rect(x - half_cw, 0, x + half_cw, arrangement_depth), "crosswall", True)
        )
    if has_stair:
        x = arrangement_width + BAY_MM
        cross_walls.append(
            WallSegment(Rect(x - half_cw, 0, x + half_cw, arrangement_depth), "crosswall", True)
        )

    # Non-load-bearing sandwich panels: front/rear exterior facades (full
    # width including the stair core), plus internal facades between
    # stacked rows in grid arrangement (units only -- the stair shaft runs
    # through uninterrupted).
    half_sw = SANDWICH_THICKNESS_MM // 2
    sandwich_walls: List[WallSegment] = []
    for r in range(rows + 1):
        y = r * unit_d
        x_end = total_width if (r == 0 or r == rows) else arrangement_width
        sandwich_walls.append(
            WallSegment(Rect(0, y - half_sw, x_end, y + half_sw), "sandwich", False)
        )

    return BuildingGeom(
        width_mm=total_width,
        depth_mm=total_depth,
        units=units,
        cross_walls=cross_walls,
        sandwich_walls=sandwich_walls,
        stair_core=stair_core,
        lift_shaft=lift_shaft,
        num_storeys=num_storeys,
        num_units=num_units,
        width_bays=width_bays,
        depth_bays=depth_bays,
        arrangement=arrangement,
        rows=rows,
        cols=cols,
    )

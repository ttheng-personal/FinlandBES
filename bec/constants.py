"""Shared constants for the BEC Residential Layout Generator.

All geometry is locked to the BEC 1200mm modular grid: BAY_MM is the one
unit of length every coordinate in the model must be an integer multiple of.
"""

BAY_MM = 1200

# Real construction thickness used only for drawing wall thickness / BoM
# calculations -- never for positioning logic (positioning always uses
# BAY_MM-aligned centrelines).
CROSSWALL_THICKNESS_MM = 150
SANDWICH_THICKNESS_MM = 360

# Slab span threshold: BEC O27 hollow-core covers spans up to and including
# 7200mm; anything longer requires the deeper O32 section.
SLAB_SPAN_THRESHOLD_MM = 7200
SLAB_CODE_SHORT = "O27"
SLAB_CODE_LONG = "O32"

# BEC element type codes (Finnish naming convention).
CROSSWALL_CODE = "V"      # Väliseinä -- load-bearing partition wall
SANDWICH_CODE = "RK"      # Sisäkuorielementti, ei kantava -- non-load-bearing sandwich facade panel
STAIR_FLIGHT_CODE = "T"   # Porraselementti -- stair flight element
STAIR_LANDING_CODE = "L"  # Laattaelementti -- solid slab, stair landing

# Finnish term + English description for every BEC code used in this app,
# keyed by the codes above. Displayed as side-by-side identifier columns
# in the Element Schedule and Bill of Materials tabs.
BEC_ELEMENT_TERMS = {
    CROSSWALL_CODE: ("Väliseinä", "Load-bearing partition wall"),
    SANDWICH_CODE: ("Sisäkuorielementti (ei kantava)", "Non-load-bearing sandwich facade panel"),
    SLAB_CODE_SHORT: ("Ontelolaatta 270", "Hollow-core slab, 270mm deep"),
    SLAB_CODE_LONG: ("Ontelolaatta 320", "Hollow-core slab, 320mm deep"),
    STAIR_FLIGHT_CODE: ("Porraselementti", "Stair flight element"),
    STAIR_LANDING_CODE: ("Laattaelementti", "Solid slab (stair landing)"),
}

# Wall/panel BoM rates (kg/m², m3/m2, EUR/m2) are given per m2 of WALL
# FACE area (length x height) -- not plan footprint. A solid 150mm wall
# at 0.150 m3 concrete per m2 of face confirms this (volume/area =
# thickness exactly). Storey height is a sidebar input (see app.py) that
# feeds straight into this face-area calculation in bec/bom.py; it has
# no effect on plan geometry or any other tab.
STOREY_HEIGHT_OPTIONS_MM = {
    "2400mm (24M)": 2400,
    "2600mm (26M)": 2600,
    "2800mm (28M)": 2800,
    "3000mm (30M)": 3000,
}
DEFAULT_STOREY_HEIGHT_LABEL = "2800mm (28M)"
MAX_RECOMMENDED_STOREY_HEIGHT_MM = 3600

# Colour palette (hex)
COLORS = {
    "crosswall": "#3f3f3f",       # dark grey, load-bearing
    "sandwich": "#ede0c4",        # warm cream, exterior, non-load-bearing
    "slab_base": "#cfe8f5",       # light blue, hollow-core slab
    "slab_hatch": "#5b9bd5",      # mid blue hatch lines (span direction)
    "stair_core": "#f0b429",      # amber
    "living": "#fdfbf6",          # warm white
    "kitchen": "#fff3c4",         # pale yellow
    "bathroom": "#c9eee2",        # pale teal
    "bedroom": "#e3d9f3",         # pale lavender
    "grid_line": "#d9d9d9",
    "text": "#1a1a1a",
}

ROOM_LABELS = {
    "living": "Living Room",
    "kitchen": "Kitchen",
    "bathroom": "Bathroom",
    "bedroom": "Bedroom",
}

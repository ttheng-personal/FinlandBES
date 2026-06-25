"""BEC connection types applicable to a generated building.

These five connections apply to every configuration this app can
generate; the two stair connections only become relevant once a stair
core exists (num_storeys > 1), which is read straight off BuildingGeom.
"""

from typing import Any, Dict, List

from bec.model import BuildingGeom

ELEMENTTISUUNNITTELU_LINK = "https://www.elementtisuunnittelu.fi/liitokset/runkoliitokset"

CONNECTION_COLUMNS = ["Connection Name", "BEC Code", "Location in Building", "Link"]

_ALWAYS_ON_CONNECTIONS = [
    {
        "Connection Name": "Hollow-core slab to load-bearing wall (perpendicular)",
        "BEC Code": "DO501",
        "Location in Building": "All slab-end-to-cross-wall interfaces",
        "Link": ELEMENTTISUUNNITTELU_LINK,
    },
    {
        "Connection Name": "Hollow-core slab to load-bearing wall (parallel)",
        "BEC Code": "DO502",
        "Location in Building": "Longitudinal slab edge to party wall",
        "Link": ELEMENTTISUUNNITTELU_LINK,
    },
    {
        "Connection Name": "Hollow-core slab to sandwich panel",
        "BEC Code": "DO511",
        "Location in Building": "All slab edges at perimeter",
        "Link": ELEMENTTISUUNNITTELU_LINK,
    },
]

_STAIR_CONNECTIONS = [
    {
        "Connection Name": "Stair landing to wall",
        "BEC Code": "DL503",
        "Location in Building": "Stair core landing bearing",
        "Link": ELEMENTTISUUNNITTELU_LINK,
    },
    {
        "Connection Name": "Stair landing to wall (acoustic)",
        "BEC Code": "DL504",
        "Location in Building": "Residential acoustic separation",
        "Link": ELEMENTTISUUNNITTELU_LINK,
    },
]


def build_connection_rows(building: BuildingGeom) -> List[Dict[str, Any]]:
    rows = list(_ALWAYS_ON_CONNECTIONS)
    if building.stair_core is not None:
        rows.extend(_STAIR_CONNECTIONS)
    return rows

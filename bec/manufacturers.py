"""Finnish precast concrete manufacturer registry, per BEC element type.

All data here is static reference data, hardcoded from the
Betoniteollisuus ry member registry (betoni.com, June 2026) -- it is
never fetched dynamically.
"""

from typing import Any, Dict, List

MANUFACTURER_COLUMNS = ["Manufacturer", "Factory Locations", "Website"]

BETONI_SEARCH_URL = "https://betoni.com/valmistajat-tuotteet-ja-projektit-hakusivu/tuotehaku/"

INTRO_TEXT = (
    "Under the Finnish BES/BEC open standard, any certified manufacturer can produce these "
    "elements using the same standardised dimensions and connection details and some "
    "manufacturers specialize on certain elements. Factory selection in practice depends on "
    "project location, element type specialisation, and commercial negotiation. "
    "Manufacturer-to-element mapping based on Betoniteollisuus ry member registry "
    "(betoni.com, June 2026)."
)

FOOTER_NOTE = (
    "Factory locations shown are approximate. Always confirm product availability and lead "
    "times directly with the manufacturer."
)

MANUFACTURER_SECTIONS: List[Dict[str, Any]] = [
    {
        "code_label": "O27 / O32",
        "finnish_term": "Ontelolaatat",
        "english_description": "Hollow-core Slabs",
        "manufacturers": [
            {"Manufacturer": "Consolis Parma", "Factory Locations": "Nummela + 11 locations nationwide", "Website": "https://www.parma.fi"},
            {"Manufacturer": "Lujabetoni Oy", "Factory Locations": "21 locations nationwide", "Website": "https://www.lujabetoni.fi"},
            {"Manufacturer": "Betset-yhtiöt", "Factory Locations": "Espoo, Helsinki, Hämeenlinna, Kyyjärvi, Mikkeli, Turku + 4 more", "Website": "https://www.betset.fi"},
            {"Manufacturer": "Joutsenon Elementti Oy", "Factory Locations": "Lappeenranta", "Website": "https://www.joutsenonelementti.fi"},
            {"Manufacturer": "Kankaanpään Betoni ja Elementti Oy", "Factory Locations": "Kankaanpää", "Website": "https://www.elementti.fi"},
        ],
    },
    {
        "code_label": "V",
        "finnish_term": "Väliseinät",
        "english_description": "Load-bearing Partition Walls",
        "manufacturers": [
            {"Manufacturer": "Consolis Parma", "Factory Locations": "Nummela + 11 locations nationwide", "Website": "https://www.parma.fi"},
            {"Manufacturer": "Lujabetoni Oy", "Factory Locations": "21 locations nationwide", "Website": "https://www.lujabetoni.fi"},
            {"Manufacturer": "Rakennusbetoni- ja Elementti Oy", "Factory Locations": "Hollola", "Website": "https://www.rakennusbetoni.fi"},
            {"Manufacturer": "VaBe Oy", "Factory Locations": "(see website)", "Website": "https://www.vabe.fi"},
            {"Manufacturer": "Joutsenon Elementti Oy", "Factory Locations": "Lappeenranta", "Website": "https://www.joutsenonelementti.fi"},
        ],
    },
    {
        "code_label": "RK",
        "finnish_term": "Sisäkuoret / Sandwich-elementit",
        "english_description": "Non-load-bearing Sandwich Facade Panels",
        "manufacturers": [
            {"Manufacturer": "Consolis Parma", "Factory Locations": "Nummela + 11 locations nationwide", "Website": "https://www.parma.fi"},
            {"Manufacturer": "RB Laatuseinä Oy", "Factory Locations": "Heinola", "Website": "https://www.rakennusbetoni.fi"},
            {"Manufacturer": "NB-Seinä Oy", "Factory Locations": "(see website)", "Website": "https://www.nb-seina.fi"},
            {"Manufacturer": "Lujabetoni Oy", "Factory Locations": "21 locations nationwide", "Website": "https://www.lujabetoni.fi"},
            {"Manufacturer": "Joutsenon Elementti Oy", "Factory Locations": "Lappeenranta", "Website": "https://www.joutsenonelementti.fi"},
        ],
    },
    {
        "code_label": "T",
        "finnish_term": "Porraselementit",
        "english_description": "Stair Flight Elements",
        "manufacturers": [
            {"Manufacturer": "Consolis Parma", "Factory Locations": "Nummela + 11 locations nationwide", "Website": "https://www.parma.fi"},
            {"Manufacturer": "Lujabetoni Oy", "Factory Locations": "21 locations nationwide", "Website": "https://www.lujabetoni.fi"},
            {"Manufacturer": "Betset-yhtiöt", "Factory Locations": "Espoo, Helsinki, Hämeenlinna, Kyyjärvi, Mikkeli, Turku + 4 more", "Website": "https://www.betset.fi"},
            {"Manufacturer": "Porin Elementtitehdas Oy", "Factory Locations": "Pori", "Website": "https://www.elementtitehdas.fi"},
        ],
    },
    {
        "code_label": "L",
        "finnish_term": "Massiivilaatat",
        "english_description": "Stair Landing Slabs",
        "manufacturers": [
            {"Manufacturer": "Consolis Parma", "Factory Locations": "Nummela + 11 locations nationwide", "Website": "https://www.parma.fi"},
            {"Manufacturer": "Lujabetoni Oy", "Factory Locations": "21 locations nationwide", "Website": "https://www.lujabetoni.fi"},
            {"Manufacturer": "Betset-yhtiöt", "Factory Locations": "Espoo, Helsinki, Hämeenlinna, Kyyjärvi, Mikkeli, Turku + 4 more", "Website": "https://www.betset.fi"},
            {"Manufacturer": "Porin Elementtitehdas Oy", "Factory Locations": "Pori", "Website": "https://www.elementtitehdas.fi"},
        ],
    },
]


def expander_label(section: Dict[str, Any]) -> str:
    count = len(section["manufacturers"])
    return (
        f"{section['code_label']} · {section['finnish_term']} · "
        f"{section['english_description']} · {count} manufacturers"
    )

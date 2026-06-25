"""Excel export for the Bill of Materials: 3 sheets -- Element BoM,
Materials Summary, Building Configuration."""

import io
from datetime import datetime
from typing import Any, Dict

import pandas as pd

from bec.bom import build_bom_df, build_bom_summary
from bec.model import BuildingGeom


def build_excel_export(building: BuildingGeom, config: Dict[str, Any], storey_height_mm: int) -> bytes:
    bom_df = build_bom_df(building, storey_height_mm)
    summary = build_bom_summary(bom_df)
    bom_with_total = pd.concat([bom_df, pd.DataFrame([summary])], ignore_index=True)

    materials_summary_df = pd.DataFrame(
        [
            ("Total Quantity (pieces)", summary["Quantity"]),
            ("Total Weight (tonnes)", summary["Total Weight (tonnes)"]),
            ("Concrete Volume (m³)", summary["Concrete Volume (m³)"]),
            ("Reinforcement Steel (kg)", summary["Reinforcement Steel (kg)"]),
            ("Insulation Area (m²)", summary["Insulation Area (m²)"]),
            ("Total Cost (EUR)", summary["Total Cost (EUR)"]),
        ],
        columns=["Metric", "Value"],
    )

    config_rows = list(config.items()) + [("Export timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))]
    config_df = pd.DataFrame(config_rows, columns=["Setting", "Value"])

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        bom_with_total.to_excel(writer, sheet_name="Element BoM", index=False)
        materials_summary_df.to_excel(writer, sheet_name="Materials Summary", index=False)
        config_df.to_excel(writer, sheet_name="Building Configuration", index=False)

    return buffer.getvalue()

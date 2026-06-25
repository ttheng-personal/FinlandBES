import pandas as pd
import streamlit as st

from bec.bom import build_bom_df, build_bom_summary
from bec.connections import CONNECTION_COLUMNS, build_connection_rows
from bec.constants import BAY_MM, DEFAULT_STOREY_HEIGHT_LABEL, MAX_RECOMMENDED_STOREY_HEIGHT_MM, STOREY_HEIGHT_OPTIONS_MM
from bec.export import build_excel_export
from bec.model import build_building
from bec.plotting import render_floor_plan
from bec.schedule import build_element_schedule_df
from bec.summary import (
    arrangement_label,
    bedroom_rooms,
    gross_floor_area_per_storey_m2,
    room_by_kind,
    room_net_area_m2,
    total_dwellings,
    total_gfa_m2,
    unit_net_area_m2,
)

st.set_page_config(page_title="BEC Residential Layout Generator", layout="wide", page_icon="🏗️")

st.title("BEC Residential Layout Generator")
st.caption(
    "Finnish BES/BEC precast concrete residential layouts, generated automatically "
    "and locked to the 1200mm modular grid."
)

with st.sidebar:
    st.header("Building configuration")

    num_units = st.slider("Number of units", min_value=2, max_value=6, value=4)
    num_storeys = st.slider("Number of storeys", min_value=1, max_value=4, value=2)

    storey_height_label = st.selectbox(
        "Storey height (floor-to-floor)",
        options=list(STOREY_HEIGHT_OPTIONS_MM.keys()),
        index=list(STOREY_HEIGHT_OPTIONS_MM.keys()).index(DEFAULT_STOREY_HEIGHT_LABEL),
    )
    st.caption(f"BEC module: 1M = 100mm. Max recommended: {MAX_RECOMMENDED_STOREY_HEIGHT_MM:,}mm.")
    storey_height_mm = STOREY_HEIGHT_OPTIONS_MM[storey_height_label]

    width_bays = st.slider("Unit width (bays)", min_value=3, max_value=5, value=4)
    st.caption(f"{width_bays} bays × 1200mm = **{width_bays * BAY_MM / 1000:.1f} m**")

    depth_bays = st.slider("Unit depth (bays)", min_value=5, max_value=8, value=6)
    st.caption(f"{depth_bays} bays × 1200mm = **{depth_bays * BAY_MM / 1000:.1f} m**")

    grid_allowed = num_units in (4, 6)
    arrangement_options = ["Row"] + (["2×2 Grid"] if grid_allowed else [])

    if "arrangement_choice" not in st.session_state or st.session_state["arrangement_choice"] not in arrangement_options:
        st.session_state["arrangement_choice"] = "Row"

    arrangement_choice = st.radio("Arrangement", arrangement_options, key="arrangement_choice")

    if not grid_allowed:
        st.caption("Grid arrangement is only available for 4 or 6 units.")
    elif arrangement_choice == "2×2 Grid":
        rows = num_units // 2
        st.caption(f"{num_units} units → 2 columns × {rows} rows.")

    arrangement = "grid" if arrangement_choice == "2×2 Grid" else "row"

    with st.expander("Hard rules enforced"):
        st.markdown(
            "1. Every coordinate is a multiple of **1200mm** — grid lock is absolute.\n"
            "2. Hollow-core slabs always span **between** load-bearing cross-walls, "
            "never parallel to them.\n"
            "3. Exterior sandwich panels are **never** load-bearing."
        )

building = build_building(
    num_units=num_units,
    num_storeys=num_storeys,
    width_bays=width_bays,
    depth_bays=depth_bays,
    arrangement=arrangement,
)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Floor Plan", "Element Schedule", "Building Summary", "Connections Used", "Bill of Materials"]
)

with tab1:
    config_bits = [
        f"{num_units} units",
        f"{num_storeys} storey{'s' if num_storeys > 1 else ''}",
        f"{width_bays}×{depth_bays} bay unit",
        "Row" if arrangement == "row" else f"Grid ({building.cols}×{building.rows})",
    ]
    st.subheader("2D Floor Plan")
    st.caption(" · ".join(config_bits))

    storey_index = 1
    if building.num_storeys > 1:
        storey_index = st.radio(
            "Storey",
            options=list(range(1, building.num_storeys + 1)),
            format_func=lambda s: f"Storey {s}",
            horizontal=True,
        )

    fig = render_floor_plan(building, storey_index=storey_index, config_label=" · ".join(config_bits))
    st.pyplot(fig, use_container_width=False)

    col1, col2, col3 = st.columns(3)
    col1.metric("Building width", f"{building.width_mm / 1000:.1f} m", f"{building.width_mm} mm")
    col2.metric("Building depth", f"{building.depth_mm / 1000:.1f} m", f"{building.depth_mm} mm")
    col3.metric("Footprint", f"{building.width_mm * building.depth_mm / 1_000_000:.1f} m²")

with tab2:
    st.subheader("Element Schedule")
    st.caption(" · ".join(config_bits))
    st.caption(
        "Hollow-core slab code: O27 for unit width ≤ 6 bays (7,200mm), O32 for wider spans."
    )
    schedule_df = build_element_schedule_df(building)
    st.dataframe(schedule_df, hide_index=True, use_container_width=True)

with tab3:
    st.subheader("Building Summary")
    st.caption(" · ".join(config_bits))

    representative_unit = building.units[0]
    living = room_by_kind(representative_unit, "living")
    kitchen = room_by_kind(representative_unit, "kitchen")
    bathroom = room_by_kind(representative_unit, "bathroom")
    bedrooms = bedroom_rooms(representative_unit)

    left_rows = [
        ("Total footprint (incl. stair core)", f"{building.width_mm / 1000:.1f} m × {building.depth_mm / 1000:.1f} m"),
        ("Gross Floor Area per storey", f"{gross_floor_area_per_storey_m2(building):.1f} m²"),
        ("Total GFA (all storeys)", f"{total_gfa_m2(building):.1f} m²"),
        ("Number of dwellings", f"{total_dwellings(building)}"),
        ("Arrangement", arrangement_label(building)),
    ]

    right_rows = [
        ("Net unit area (excl. walls)", f"{unit_net_area_m2(representative_unit):.1f} m²"),
        ("Living room", f"{room_net_area_m2(living, representative_unit):.1f} m²"),
        ("Kitchen", f"{room_net_area_m2(kitchen, representative_unit):.1f} m²"),
        ("Bathroom", f"{room_net_area_m2(bathroom, representative_unit):.1f} m²"),
    ]
    for i, bed in enumerate(bedrooms, start=1):
        right_rows.append((f"Bedroom {i}", f"{room_net_area_m2(bed, representative_unit):.1f} m²"))

    total_habitable = unit_net_area_m2(representative_unit)
    right_rows.append(("Total net habitable area", f"{total_habitable:.1f} m²"))

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("**Building dimensions**")
        st.dataframe(
            pd.DataFrame(left_rows, columns=["Metric", "Value"]),
            hide_index=True, use_container_width=True,
        )
    with col_right:
        st.markdown("**Per dwelling**")
        st.dataframe(
            pd.DataFrame(right_rows, columns=["Metric", "Value"]),
            hide_index=True, use_container_width=True,
        )

    st.caption(
        "Net areas measured to inside face of structural walls. Wall thickness "
        "(150mm cross-walls, 360mm sandwich panels) is excluded from habitable area."
    )

with tab4:
    st.subheader("Connections Used")
    st.caption(" · ".join(config_bits))

    conn_df = pd.DataFrame(build_connection_rows(building), columns=CONNECTION_COLUMNS)
    st.dataframe(
        conn_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Link": st.column_config.LinkColumn("Link", display_text="elementtisuunnittelu.fi")
        },
    )
    st.caption("Connection details and DWG downloads available at elementtisuunnittelu.fi")

with tab5:
    st.subheader("Bill of Materials")
    st.caption(" · ".join(config_bits))

    st.warning(
        "⚠️ Unit costs are indicative Finnish market rates (2024). Actual costs vary by "
        "manufacturer, finish, transport distance and site conditions. Do not use for procurement."
    )

    bom_df = build_bom_df(building, storey_height_mm)
    st.dataframe(bom_df, hide_index=True, use_container_width=True)

    bom_summary = build_bom_summary(bom_df)
    st.markdown("**Totals**")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total weight", f"{bom_summary['Total Weight (tonnes)']:.1f} t")
    m2.metric("Concrete volume", f"{bom_summary['Concrete Volume (m³)']:.1f} m³")
    m3.metric("Reinforcement steel", f"{bom_summary['Reinforcement Steel (kg)']:.0f} kg")
    m4.metric("Insulation area", f"{bom_summary['Insulation Area (m²)']:.1f} m²")
    m5.metric("Total cost", f"€{bom_summary['Total Cost (EUR)']:.0f}")

    export_config = {
        "Number of units": num_units,
        "Number of storeys": num_storeys,
        "Storey height (mm)": storey_height_mm,
        "Unit width (bays)": width_bays,
        "Unit width (m)": round(width_bays * BAY_MM / 1000, 1),
        "Unit depth (bays)": depth_bays,
        "Unit depth (m)": round(depth_bays * BAY_MM / 1000, 1),
        "Arrangement": arrangement_label(building),
    }
    excel_bytes = build_excel_export(building, export_config, storey_height_mm)
    st.download_button(
        "Download Bill of Materials (Excel)",
        data=excel_bytes,
        file_name="bec_bill_of_materials.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

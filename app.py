import pandas as pd
import streamlit as st

from bec.bom import build_bom_df, build_bom_summary
from bec.carbon import (
    build_carbon_df,
    build_carbon_rows,
    carbon_summary,
    render_benchmark_bar,
    render_carbon_chart,
)
from bec.compliance import (
    ADVISORY,
    FAIL,
    INFO,
    PASS,
    build_compliance_rules,
    compliance_summary,
    format_rule_message,
)
from bec.connections import CONNECTION_COLUMNS, build_connection_rows
from bec.constants import BAY_MM, DEFAULT_STOREY_HEIGHT_LABEL, MAX_RECOMMENDED_STOREY_HEIGHT_MM, STOREY_HEIGHT_OPTIONS_MM
from bec.export import build_excel_export
from bec.manufacturers import (
    BETONI_SEARCH_URL,
    FOOTER_NOTE,
    INTRO_TEXT,
    MANUFACTURER_COLUMNS,
    MANUFACTURER_SECTIONS,
    expander_label,
)
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

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
    [
        "Floor Plan", "Element Schedule", "Building Summary", "Connections Used",
        "Bill of Materials", "Embodied Carbon", "Manufacturers", "BEC Compliance Checker",
    ]
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

    footprint_label = (
        "Total footprint (incl. stair core & lift shaft)" if building.lift_shaft is not None
        else "Total footprint (incl. stair core)"
    )
    left_rows = [
        (footprint_label, f"{building.width_mm / 1000:.1f} m × {building.depth_mm / 1000:.1f} m"),
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
    if building.lift_shaft is not None:
        st.caption(
            "Lift shaft included — mandatory for buildings of 4 or more storeys "
            "(Finnish building code)."
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

with tab6:
    st.subheader("Embodied Carbon")
    st.caption(" · ".join(config_bits))

    st.warning(
        "⚠️ Carbon values are indicative, derived from Finnish precast industry EPD data "
        "(EN 15804, A1–A3 product stage). They cover raw material extraction, transport to "
        "factory, and manufacturing only. Installation, transport to site, and end-of-life "
        "are excluded. Do not use for formal carbon assessments or Green Mark submissions."
    )

    carbon_rows = build_carbon_rows(building, storey_height_mm)
    carbon_stats = carbon_summary(carbon_rows, building)

    st.markdown("**Carbon Summary**")
    cc1, cc2, cc3, cc4 = st.columns(4)
    cc1.metric("Total embodied carbon", f"{carbon_stats['total_carbon_tonnes']:.1f} tCO₂e")
    cc2.metric("Carbon intensity", f"{carbon_stats['intensity_kg_m2_gfa']:.0f} kgCO₂e/m² GFA")
    cc3.metric(
        "Heaviest contributor", carbon_stats["heaviest_type"],
        f"{carbon_stats['heaviest_pct']:.0f}% of total", delta_color="off",
    )
    cc4.metric(
        "Scale-adjusted benchmark", f"~{carbon_stats['benchmark_kg_m2_gfa']:.0f} kgCO₂e/m² GFA",
        "structural shell only", delta_color="off",
    )

    benchmark_fig = render_benchmark_bar(
        carbon_stats["intensity_kg_m2_gfa"], carbon_stats["benchmark_kg_m2_gfa"], carbon_stats["benchmark_status"]
    )
    st.pyplot(benchmark_fig, use_container_width=False)
    st.caption(
        "Benchmark varies by building scale. Small buildings typically show higher kgCO₂e/m² GFA "
        "due to higher wall-to-floor-area ratios — this reflects geometry, not inefficiency in the "
        "precast system. Current applicable benchmark for this configuration: "
        f"{carbon_stats['benchmark_kg_m2_gfa']:.0f} kgCO₂e/m² GFA."
    )

    st.markdown("**Carbon Breakdown**")
    carbon_df = build_carbon_df(building, storey_height_mm)
    st.dataframe(carbon_df, hide_index=True, use_container_width=True)

    st.markdown("**Carbon Breakdown Chart**")
    carbon_chart_fig = render_carbon_chart(carbon_rows)
    st.pyplot(carbon_chart_fig, use_container_width=False)

    st.caption(
        "Precast concrete construction typically achieves 15–25% lower embodied carbon than "
        "equivalent cast-in-situ construction, due to optimised factory mix designs, reduced "
        "formwork waste, and precise material quantities. Source: Betoniteollisuus ry / "
        "Finnish Concrete Industry Association."
    )

with tab7:
    st.subheader("Manufacturers")
    st.caption(" · ".join(config_bits))

    st.info(INTRO_TEXT)

    for section in MANUFACTURER_SECTIONS:
        with st.expander(expander_label(section)):
            mfr_df = pd.DataFrame(section["manufacturers"], columns=MANUFACTURER_COLUMNS)
            st.dataframe(
                mfr_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Website": st.column_config.LinkColumn("Website", display_text=r"https://(.*)")
                },
            )

    st.caption(FOOTER_NOTE)
    st.link_button("Search live manufacturer database →", url=BETONI_SEARCH_URL)

with tab8:
    st.subheader("BEC Compliance Checker")
    st.caption(" · ".join(config_bits))

    rules = build_compliance_rules(building, storey_height_mm)
    summary = compliance_summary(rules)

    st.markdown(
        f"""<div style="background:#f0f4f8;border:1px solid #c8d6e5;border-radius:8px;"""
        f"""padding:12px 20px;margin-bottom:4px;font-size:1.05em;">"""
        f"""✅ <strong>{summary[PASS]} Passed</strong> &nbsp;·&nbsp; """
        f"""⚠️ <strong>{summary[ADVISORY]} Advisory</strong> &nbsp;·&nbsp; """
        f"""❌ <strong>{summary[FAIL]} Failed</strong>"""
        f"""</div>""",
        unsafe_allow_html=True,
    )

    status_renderer = {
        PASS: st.success,
        ADVISORY: st.warning,
        FAIL: st.error,
        INFO: st.info,
    }

    sections = ["Structural Rules", "Dimensional Rules", "Open-Standard Compliance"]
    for section in sections:
        st.markdown(f"### {section}")
        for rule in rules:
            if rule["section"] != section:
                continue
            status_renderer[rule["status"]](format_rule_message(rule))

    st.markdown(
        f"**✅ {summary[PASS]} rules passed · ⚠️ {summary[ADVISORY]} advisory · "
        f"❌ {summary[FAIL]} failed**"
    )
    if summary[ADVISORY] == 0 and summary[FAIL] == 0:
        st.success(
            "This configuration is fully BEC/BES compliant. All elements can be "
            "manufactured and assembled using the open Finnish precast standard."
        )

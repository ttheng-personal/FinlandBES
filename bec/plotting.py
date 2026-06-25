"""2D floor plan renderer for a BuildingGeom, drawn with matplotlib."""

from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure

from bec.constants import BAY_MM, COLORS
from bec.model import BuildingGeom


def _mm_to_m(mm: int) -> str:
    return f"{mm / 1000:.1f} m"


def _add_room(ax, rect, color, label, alpha=0.55):
    ax.add_patch(
        mpatches.Rectangle(
            (rect.x0, rect.y0), rect.width, rect.depth,
            facecolor=color, edgecolor="#333333", linewidth=0.8, alpha=alpha, zorder=4,
        )
    )
    cx, cy = rect.x0 + rect.width / 2, rect.y0 + rect.depth / 2
    fontsize = 7.5 if (rect.width >= 1800 and rect.depth >= 1800) else 6
    ax.text(
        cx, cy, f"{label}\n{rect.width}×{rect.depth}mm",
        ha="center", va="center", fontsize=fontsize, color=COLORS["text"], zorder=6,
        linespacing=1.4,
    )


def _add_slab(ax, rect, depth_bays: int):
    ax.add_patch(
        mpatches.Rectangle(
            (rect.x0, rect.y0), rect.width, rect.depth,
            facecolor=COLORS["slab_base"], edgecolor="none", alpha=0.75, zorder=1,
        )
    )
    # Hatch lines run ALONG the span direction (the unit width / x-axis),
    # repeated at every bay row -- this is the slab joint pattern, never
    # drawn parallel to the load-bearing cross-walls that support it.
    # Drawn at zorder 3 (above the slab fill, below room labels) so the
    # span direction stays legible through the semi-transparent room fill.
    for k in range(depth_bays + 1):
        y = rect.y0 + k * BAY_MM
        ax.plot(
            [rect.x0, rect.x1], [y, y],
            color=COLORS["slab_hatch"], linewidth=1.0, alpha=0.9, zorder=3,
        )


def _add_wall(ax, wall):
    color = COLORS["crosswall"] if wall.kind == "crosswall" else COLORS["sandwich"]
    ax.add_patch(
        mpatches.Rectangle(
            (wall.rect.x0, wall.rect.y0), wall.rect.width, wall.rect.depth,
            facecolor=color, edgecolor="#111111", linewidth=0.4, zorder=5,
        )
    )


def _draw_grid(ax, width_mm: int, depth_mm: int):
    x = 0
    while x <= width_mm:
        ax.axvline(x, color=COLORS["grid_line"], linewidth=0.4, zorder=0)
        x += BAY_MM
    y = 0
    while y <= depth_mm:
        ax.axhline(y, color=COLORS["grid_line"], linewidth=0.4, zorder=0)
        y += BAY_MM


def _dimension_line(ax, p0, p1, text, offset, vertical=False):
    """Draw an architectural-style dimension line with end ticks and a label."""
    if vertical:
        x = p0[0] + offset
        y0, y1 = p0[1], p1[1]
        ax.annotate(
            "", xy=(x, y1), xytext=(x, y0),
            arrowprops=dict(arrowstyle="<->", color="#444444", linewidth=0.8), zorder=7,
        )
        ax.text(x + (40 if offset > 0 else -40), (y0 + y1) / 2, text, rotation=90,
                ha="center", va="center", fontsize=8, color="#222222", zorder=7)
    else:
        y = p0[1] + offset
        x0, x1 = p0[0], p1[0]
        ax.annotate(
            "", xy=(x1, y), xytext=(x0, y),
            arrowprops=dict(arrowstyle="<->", color="#444444", linewidth=0.8), zorder=7,
        )
        ax.text((x0 + x1) / 2, y + (200 if offset > 0 else -300), text,
                ha="center", va="center", fontsize=8, color="#222222", zorder=7)


def _scale_bar(ax, x0, y0, length_mm=2000):
    ax.plot([x0, x0 + length_mm], [y0, y0], color="black", linewidth=2, zorder=7)
    for x in (x0, x0 + length_mm):
        ax.plot([x, x], [y0 - 80, y0 + 80], color="black", linewidth=2, zorder=7)
    ax.text(x0 + length_mm / 2, y0 - 350, f"{length_mm / 1000:.0f} m", ha="center", fontsize=8, zorder=7)


def _north_arrow(ax, x, y, size=600):
    ax.annotate(
        "", xy=(x, y + size), xytext=(x, y),
        arrowprops=dict(arrowstyle="-|>", color="black", linewidth=1.5), zorder=7,
    )
    ax.text(x, y + size + 200, "N", ha="center", fontsize=10, fontweight="bold", zorder=7)


def render_floor_plan(
    building: BuildingGeom,
    storey_index: int = 1,
    config_label: str = "",
) -> Figure:
    width_m = building.width_mm / 1000
    depth_m = building.depth_mm / 1000

    fig_w = max(7.0, min(16.0, 1.05 * width_m))
    fig_h = max(6.0, min(15.0, 1.05 * depth_m)) + 1.2

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    margin_x = max(1500, building.width_mm * 0.12)
    margin_top = 1600
    margin_bottom = 1400
    ax.set_xlim(-margin_x, building.width_mm + margin_x)
    ax.set_ylim(-margin_bottom, building.depth_mm + margin_top)

    _draw_grid(ax, building.width_mm, building.depth_mm)

    for unit in building.units:
        _add_slab(ax, unit.rect, building.depth_bays)
        for room in unit.rooms:
            _add_room(ax, room.rect, COLORS[room.kind], room.label)

    if building.stair_core is not None:
        sc = building.stair_core.rect
        ax.add_patch(
            mpatches.Rectangle(
                (sc.x0, sc.y0), sc.width, sc.depth,
                facecolor=COLORS["stair_core"], edgecolor="#333333", linewidth=0.8, zorder=4,
            )
        )
        ax.text(
            sc.x0 + sc.width / 2, sc.y0 + sc.depth / 2,
            f"STAIR\nCORE\n{sc.width}×{sc.depth}mm",
            ha="center", va="center", fontsize=7, rotation=90, color=COLORS["text"], zorder=6,
        )

    for wall in building.sandwich_walls:
        _add_wall(ax, wall)
    for wall in building.cross_walls:
        _add_wall(ax, wall)

    # Overall dimensions
    _dimension_line(ax, (0, building.depth_mm), (building.width_mm, building.depth_mm),
                     f"{building.width_mm}mm ({_mm_to_m(building.width_mm)})", offset=900)
    _dimension_line(ax, (building.width_mm, 0), (building.width_mm, building.depth_mm),
                     f"{building.depth_mm}mm ({_mm_to_m(building.depth_mm)})", offset=900, vertical=True)

    _scale_bar(ax, 0, -margin_bottom + 350)
    _north_arrow(ax, building.width_mm + margin_x - 500, building.depth_mm - 1800)

    legend_handles = [
        mpatches.Patch(color=COLORS["crosswall"], label="Load-bearing cross-wall"),
        mpatches.Patch(color=COLORS["sandwich"], label="Sandwich panel (exterior, non-load-bearing)"),
        mpatches.Patch(color=COLORS["slab_base"], label="Hollow-core slab (hatch = span direction)"),
        mpatches.Patch(color=COLORS["stair_core"], label="Stair core"),
        mpatches.Patch(color=COLORS["living"], label="Living room"),
        mpatches.Patch(color=COLORS["kitchen"], label="Kitchen"),
        mpatches.Patch(color=COLORS["bathroom"], label="Bathroom"),
        mpatches.Patch(color=COLORS["bedroom"], label="Bedroom"),
    ]
    ax.legend(
        handles=legend_handles, loc="upper center", bbox_to_anchor=(0.5, -0.06),
        ncol=4, fontsize=7.5, frameon=False,
    )

    ax.set_aspect("equal")
    ax.set_xticks(range(0, building.width_mm + 1, BAY_MM))
    ax.set_yticks(range(0, building.depth_mm + 1, BAY_MM))
    ax.tick_params(labelsize=6)
    ax.set_xlabel("mm", fontsize=8)
    ax.set_ylabel("mm", fontsize=8)

    title = f"Storey {storey_index}" if building.num_storeys > 1 else "Floor Plan"
    if config_label:
        title += f" — {config_label}"
    ax.set_title(title, fontsize=11, fontweight="bold")

    fig.tight_layout()
    return fig

#!/usr/bin/env python3
"""
Date-palm-frond bowl with golden dates — parametric generator.

Produces a printable two-colour model for the Bambu Lab P2S (or any
multi-material printer):

  * leaf   (green)  – a pinnate date-palm frond spread out as a shallow,
                      concave bowl with a flat foot, raised midrib and
                      leaflet veins.
  * dates  (gold)   – a ring of dates lying on the inner slope of the bowl,
                      partly sunk into the leaf so they fuse when printed.

Outputs (all in millimetres):
  date_palm_bowl.3mf                  – one object, two parts, colours attached
  date_palm_bowl_leaf_green.stl       – leaf only
  date_palm_bowl_dates_gold.stl       – dates only
  preview.png                         – rendered preview

Run:  python3 generate_date_palm_bowl.py
Deps: numpy shapely trimesh triangle matplotlib
"""
from __future__ import annotations

import os
import zipfile
from xml.sax.saxutils import escape

import numpy as np
import shapely
import trimesh
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# Parameters (mm)
# --------------------------------------------------------------------------
A, B = 85.0, 58.0            # outline ellipse semi-axes (leaflet tips)
A0, B0 = 60.0, 33.0          # flat foot ellipse semi-axes (25 mm run to rim)
SLOPE0 = 1.0                 # initial wall slope (1.0 = 45°, no supports)
SLOPE_K = 0.005              # quadratic steepening of the wall
THICK = 3.0                  # vertical shell thickness
RIB_H, RIB_W = 1.6, 2.6      # midrib ridge height / half-width
VEIN_H, VEIN_W = 0.8, 1.1    # leaflet vein ridge height / half-width
LEAFLET_STEP = 6.0           # spacing of leaflets along the midrib
LEAFLET_HALF_W = 7.0         # max half-width of a leaflet (overlaps neighbour)
WEB = 8.0                    # solid web: notches between leaflet tips never deeper than this
N_DATES = 16
DATE_L, DATE_W = 19.0, 10.0  # date length / diameter
DATE_RING = 10.0             # ring sits this far out from the foot ellipse
DATE_LIFT = 3.2              # date centre above surface (semi-axis is 5 → 1.8 sunk)
TRI_ARGS = "pq30a1.2"        # triangle: quality 30°, max area 1.2 mm²

GREEN = "#2F7D3A"
GOLD = "#D4AF37"


# --------------------------------------------------------------------------
# 2-D silhouette of the frond
# --------------------------------------------------------------------------
def leaflet_polygon(p0, direction, length, half_w):
    """Lanceolate leaflet starting at p0 running `length` along `direction`."""
    d = np.asarray(direction, float)
    d /= np.linalg.norm(d)
    n = np.array([-d[1], d[0]])
    u = np.linspace(0.0, 1.0, 24)
    # narrow base, widest at ~40 %, pointed tip
    w = half_w * np.sin(np.pi * u ** 0.6) ** 0.8
    w[0] = half_w * 0.4
    w[-1] = 0.0
    pts_l = [p0 + d * (length * ui) + n * wi for ui, wi in zip(u, w)]
    pts_r = [p0 + d * (length * ui) - n * wi for ui, wi in zip(u[::-1], w[::-1])]
    return Polygon(np.vstack([pts_l, pts_r]))


def ellipse_hit(p0, direction):
    """Distance along `direction` from p0 to the outline ellipse."""
    dx, dy = direction / np.linalg.norm(direction)
    x0, y0 = p0
    qa = (dx / A) ** 2 + (dy / B) ** 2
    qb = 2 * (x0 * dx / A ** 2 + y0 * dy / B ** 2)
    qc = (x0 / A) ** 2 + (y0 / B) ** 2 - 1.0
    disc = qb * qb - 4 * qa * qc
    return (-qb + np.sqrt(disc)) / (2 * qa)


def build_silhouette():
    parts = []
    veins = []  # list of (p_start, p_end) centre-lines for vein relief

    # solid web under the leaflets (keeps the rim notches shallow), midrib, petiole stub
    t = np.linspace(0, 2 * np.pi, 360, endpoint=False)
    parts.append(Polygon(np.c_[(A - WEB) * np.cos(t), (B - WEB) * np.sin(t)]))
    parts.append(box(-92.0, -3.0, 76.0, 3.0))
    petiole = Polygon([(-92, -4.5), (-74, -4.5), (-74, 4.5), (-92, 4.5)]).buffer(2.0)
    parts.append(petiole)

    rng = np.random.default_rng(7)
    xs = np.arange(-78.0, 70.0 + 1e-6, LEAFLET_STEP)
    for i, x in enumerate(xs):
        frac = (x - xs[0]) / (xs[-1] - xs[0])            # 0 at base → 1 at tip
        theta = np.deg2rad(84.0 - 50.0 * frac)            # forward angle
        for side in (+1.0, -1.0):
            x_att = x + (LEAFLET_STEP * 0.5 if side < 0 else 0.0)  # alternate
            if x_att > 70.5:
                continue
            p0 = np.array([x_att, 0.0])
            d = np.array([np.cos(theta), side * np.sin(theta)])
            length = ellipse_hit(p0, d) * (1.0 + rng.uniform(-0.03, 0.04))
            parts.append(leaflet_polygon(p0, d, length, LEAFLET_HALF_W))
            veins.append((p0 + d * 3.0, p0 + d * (length - 2.5)))

    # terminal leaflet along the axis
    p0 = np.array([66.0, 0.0])
    d = np.array([1.0, 0.0])
    length = ellipse_hit(p0, d)
    parts.append(leaflet_polygon(p0, d, length, 4.5))

    union = unary_union(parts)
    if union.geom_type == "MultiPolygon":
        union = max(union.geoms, key=lambda g: g.area)
    outline = Polygon(union.exterior).simplify(0.12)
    return outline, veins


# --------------------------------------------------------------------------
# Height field of the bowl
# --------------------------------------------------------------------------
def make_foot():
    t = np.linspace(0, 2 * np.pi, 400, endpoint=False)
    return Polygon(np.c_[A0 * np.cos(t), B0 * np.sin(t)])


FOOT = make_foot()


def bowl_height(xy):
    """z of the bowl's underside at points xy (N,2)."""
    pts = shapely.points(xy)
    d = shapely.distance(pts, FOOT)          # 0 inside the foot
    return SLOPE0 * d + SLOPE_K * d * d


def surface_normal(xy, eps=0.05):
    xy = np.atleast_2d(xy)
    zx = (bowl_height(xy + [eps, 0]) - bowl_height(xy - [eps, 0])) / (2 * eps)
    zy = (bowl_height(xy + [0, eps]) - bowl_height(xy - [0, eps])) / (2 * eps)
    n = np.c_[-zx, -zy, np.ones(len(xy))]
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def seg_dist(p, a, b):
    """Distance from points p (N,2) to segment a-b."""
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0.0, 1.0)
    proj = a + t[:, None] * ab
    return np.linalg.norm(p - proj, axis=1)


def vein_relief(xy, veins):
    bump = RIB_H * np.exp(-(seg_dist(xy, np.array([-92.0, 0.0]), np.array([84.0, 0.0])) / RIB_W) ** 2)
    for a, b in veins:
        v = VEIN_H * np.exp(-(seg_dist(xy, np.asarray(a), np.asarray(b)) / VEIN_W) ** 2)
        bump = np.maximum(bump, v)
    return bump


# --------------------------------------------------------------------------
# Meshes
# --------------------------------------------------------------------------
def build_leaf():
    outline, veins = build_silhouette()
    slab = trimesh.creation.extrude_polygon(outline, height=THICK, engine="triangle", triangle_args=TRI_ARGS)
    v = slab.vertices.copy()
    top = v[:, 2] > THICK * 0.5
    z_shift = bowl_height(v[:, :2])
    v[:, 2] += z_shift
    v[top, 2] += vein_relief(v[top, :2], veins)
    leaf = trimesh.Trimesh(v, slab.faces, process=True)
    leaf.fix_normals()
    return leaf, outline


def build_date():
    s = trimesh.creation.icosphere(subdivisions=3)
    v = s.vertices.copy()
    # ellipsoid, slightly narrower at one end, gentle ridge like a real date
    v[:, 0] *= DATE_L / 2
    taper = 1.0 - 0.18 * np.clip(v[:, 0] / (DATE_L / 2), 0, 1) ** 2
    v[:, 1] *= DATE_W / 2 * taper
    v[:, 2] *= DATE_W / 2 * taper
    return trimesh.Trimesh(v, s.faces, process=True)


def build_dates():
    proto = build_date()
    meshes = []
    ra, rb = A0 + DATE_RING, B0 + DATE_RING
    rng = np.random.default_rng(3)
    for j in range(N_DATES):
        phi = 2 * np.pi * (j + 0.5) / N_DATES
        p = np.array([ra * np.cos(phi), rb * np.sin(phi)])
        tangent = np.array([-ra * np.sin(phi), rb * np.cos(phi), 0.0])
        tangent /= np.linalg.norm(tangent)
        n = surface_normal(p)[0]
        # small random twist about the normal for a natural look
        ang = rng.uniform(-0.25, 0.25)
        tangent = trimesh.transformations.rotation_matrix(ang, n)[:3, :3] @ tangent
        tangent -= n * (tangent @ n)
        tangent /= np.linalg.norm(tangent)
        y_axis = np.cross(n, tangent)
        R = np.c_[tangent, y_axis, n]
        z_surf = bowl_height(p[None, :])[0] + THICK
        centre = np.array([p[0], p[1], z_surf]) + n * DATE_LIFT
        m = proto.copy()
        m.vertices = m.vertices @ R.T + centre
        meshes.append(m)
    dates = trimesh.util.concatenate(meshes)
    dates.fix_normals()
    return dates


# --------------------------------------------------------------------------
# 3MF writer (generic, with colours and one multi-part object)
# --------------------------------------------------------------------------
def write_3mf(path, parts):
    """parts: list of (name, mesh, hex_colour)."""
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<model unit="millimeter" xml:lang="en-US" '
           'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
           ' <metadata name="Title">Date palm frond bowl with dates</metadata>',
           ' <metadata name="Application">generate_date_palm_bowl.py</metadata>',
           ' <resources>',
           '  <basematerials id="1">']
    for name, _, colour in parts:
        xml.append(f'   <base name="{escape(name)}" displaycolor="{colour}FF" />')
    xml.append('  </basematerials>')
    for idx, (name, mesh, _) in enumerate(parts):
        oid = idx + 2
        xml.append(f'  <object id="{oid}" name="{escape(name)}" type="model" pid="1" pindex="{idx}">')
        xml.append('   <mesh>')
        xml.append('    <vertices>')
        xml.extend(f'     <vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}" />' for x, y, z in mesh.vertices)
        xml.append('    </vertices>')
        xml.append('    <triangles>')
        xml.extend(f'     <triangle v1="{a}" v2="{b}" v3="{c}" />' for a, b, c in mesh.faces)
        xml.append('    </triangles>')
        xml.append('   </mesh>')
        xml.append('  </object>')
    asm_id = len(parts) + 2
    xml.append(f'  <object id="{asm_id}" name="Date palm bowl" type="model">')
    xml.append('   <components>')
    for idx in range(len(parts)):
        xml.append(f'    <component objectid="{idx + 2}" />')
    xml.append('   </components>')
    xml.append('  </object>')
    xml.append(' </resources>')
    xml.append(' <build>')
    xml.append(f'  <item objectid="{asm_id}" />')
    xml.append(' </build>')
    xml.append('</model>')

    content_types = ('<?xml version="1.0" encoding="UTF-8"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />'
                     '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml" />'
                     '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" />'
            '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", "\n".join(xml))


# --------------------------------------------------------------------------
# Preview render
# --------------------------------------------------------------------------
def render_preview(path, parts):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    light = np.array([0.4, -0.5, 0.75])
    light /= np.linalg.norm(light)

    fig = plt.figure(figsize=(16, 5.5), dpi=110)
    views = [(32, -55, "isometric"), (90, -90, "top"), (8, -90, "side")]
    for k, (elev, azim, title) in enumerate(views):
        ax = fig.add_subplot(1, 3, k + 1, projection="3d")
        tris, cols = [], []
        for _, mesh, colour in parts:
            base = np.array(to_rgb(colour))
            shade = 0.45 + 0.55 * np.clip(mesh.face_normals @ light, 0, 1)
            tris.append(mesh.triangles)
            cols.append(base[None, :] * shade[:, None])
        tris = np.vstack(tris)
        cols = np.vstack(cols)
        coll = Poly3DCollection(tris, facecolors=cols, edgecolors="none", zsort="average")
        ax.add_collection3d(coll)
        ax.set_xlim(-95, 95)
        ax.set_ylim(-65, 65)
        ax.set_zlim(0, 50)
        ax.set_box_aspect((190, 130, 50), zoom=1.45)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# --------------------------------------------------------------------------
def main():
    leaf, outline = build_leaf()
    dates = build_dates()

    for name, m in (("leaf", leaf), ("dates", dates)):
        ext = m.bounds
        print(f"{name:6s} faces={len(m.faces):6d} watertight={m.is_watertight} "
              f"winding={m.is_winding_consistent} volume={m.volume:9.0f} mm³ "
              f"size={np.round(ext[1] - ext[0], 1)}")

    # every date must sit inside the leaf outline
    for m in dates.split(only_watertight=False):
        c = m.centroid[:2]
        assert outline.contains(shapely.points(c)), f"date centre {c} outside leaf"
        assert outline.exterior.distance(shapely.points(c)) > DATE_W / 2, f"date at {c} too close to rim"

    parts = [("Palm leaf (green)", leaf, GREEN), ("Dates (gold)", dates, GOLD)]
    leaf.export(os.path.join(OUT_DIR, "date_palm_bowl_leaf_green.stl"))
    dates.export(os.path.join(OUT_DIR, "date_palm_bowl_dates_gold.stl"))
    write_3mf(os.path.join(OUT_DIR, "date_palm_bowl.3mf"), parts)
    render_preview(os.path.join(OUT_DIR, "preview.png"), parts)
    print("done")


if __name__ == "__main__":
    main()

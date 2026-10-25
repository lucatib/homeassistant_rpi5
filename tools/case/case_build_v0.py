# First parametric version of the case (v0): builds the bezel and the shell for the Elecrow 7" 1024x600 display
# plus the Raspberry Pi, around the "rpi" mesh. All dimensions in mm; coordinates = the scan's system
# (Z=0 front of the glass, +Z towards the back). Re-runnable: it recreates the components from scratch.
# Usage: set PART = 'bezel' | 'shell' | 'both' | 'check' before exec().
#
# NOTE: this is only the starting point. The final model (screw-less snap-fit bezel, interlocking band, stand,
# air pockets, ...) was refined step by step directly in Fusion: use models/RPi5 Display Case.f3d and step/*.step.
import adsk.core, adsk.fusion, math, json, traceback

app = adsk.core.Application.get()
des = adsk.fusion.Design.cast(app.activeProduct)
root = des.rootComponent
mm = lambda v: v / 10.0          # mm -> cm (Fusion's internal units)
Pt = adsk.core.Point3D.create
VI = adsk.core.ValueInput.createByReal
NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
CUT = adsk.fusion.FeatureOperations.CutFeatureOperation

# ---------------- parameters (mm) ----------------
xc, yc = 21.6, 18.2                 # centre of the panel in the scan
pcb_w, pcb_h = 164.9, 102.0         # PCB from the seller's drawing
pocket_w, pocket_h, pocket_r = 168.0, 104.6, 2.0   # pocket: PCB + clearance (the scan is wider than the PCB)
wall = 2.5
outer_w, outer_h, outer_r = pocket_w + 2 * wall, pocket_h + 2 * wall, 8.0
face_t = 2.4                        # bezel front thickness
act_w, act_h = 154.21, 85.92        # active area (seller)
win_margin, win_dx, win_dy, win_r = 1.0, 0.0, 0.0, 1.5   # window = active area + margin; dx/dy for corrections
front_fillet = 2.0
T = 11.5                            # glass front -> PCB back (from the scan)
boss_gap, boss_d = 0.5, 8.0
insert_d, insert_depth = 4.2, 6.6   # M3 heat-set insert
zj = 21.5                           # bezel/shell joint plane
back_in, back_t = 40.5, 3.0         # inner face of the back; back thickness
z_back = back_in + back_t
back_fillet = 2.5
screw_d, cbore_d, cbore_depth = 3.4, 6.6, 1.6
post_dx_bottom, post_dx_top, post_inset = 40.0, 22.0, 3.6
key_dx, key_y, key_head, key_slot_w, key_slot_len = 40.0, 56.0, 9.0, 4.5, 8.0
vent_n, vent_pitch, vent_w, vent_len, vent_cx, vent_cy = 7, 6.0, 2.6, 36.0, 10.0, 8.0

pcb_bot = yc - pcb_h / 2
# display connectors (from the drawing, measured from the PCB edge)
y_hdmi = pcb_bot + (pcb_h - 41.5)
y_touch = pcb_bot + 40.0
y_power = pcb_bot + 22.0
y_wheel = pcb_bot + 49.0
y_jack = pcb_bot + 23.16

posts = [(xc - post_dx_bottom, yc - pocket_h / 2 + post_inset),
         (xc + post_dx_bottom, yc - pocket_h / 2 + post_inset),
         (xc - post_dx_top, yc + pocket_h / 2 - post_inset),
         (xc + post_dx_top, yc + pocket_h / 2 - post_inset)]
xl_out, xl_in = xc - outer_w / 2, xc - pocket_w / 2      # left wall (x min)
xr_in, xr_out = xc + pocket_w / 2, xc + outer_w / 2      # right wall (x max)

log = []


# ---------------- helpers ----------------
def rrect(sk, cx, cy, w, h, r):
    s = math.sqrt(0.5)
    x0, x1 = mm(cx - w / 2), mm(cx + w / 2)
    y0, y1 = mm(cy - h / 2), mm(cy + h / 2)
    r = mm(r)
    L = sk.sketchCurves.sketchLines
    A = sk.sketchCurves.sketchArcs

    def seg(a, b):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) > 1e-9:
            L.addByTwoPoints(Pt(a[0], a[1], 0), Pt(b[0], b[1], 0))

    def arc(a, m, b):
        A.addByThreePoints(Pt(a[0], a[1], 0), Pt(m[0], m[1], 0), Pt(b[0], b[1], 0))

    seg((x0 + r, y0), (x1 - r, y0)); arc((x1 - r, y0), (x1 - r + r * s, y0 + r - r * s), (x1, y0 + r))
    seg((x1, y0 + r), (x1, y1 - r)); arc((x1, y1 - r), (x1 - r + r * s, y1 - r + r * s), (x1 - r, y1))
    seg((x1 - r, y1), (x0 + r, y1)); arc((x0 + r, y1), (x0 + r - r * s, y1 - r + r * s), (x0, y1 - r))
    seg((x0, y1 - r), (x0, y0 + r)); arc((x0, y0 + r), (x0 + r - r * s, y0 + r - r * s), (x0 + r, y0))


def circles(sk, centers, d):
    for (cx, cy) in centers:
        sk.sketchCurves.sketchCircles.addByCenterRadius(Pt(mm(cx), mm(cy), 0), mm(d / 2))


def rect(sk, x0, x1, y0, y1):
    sk.sketchCurves.sketchLines.addTwoPointRectangle(Pt(mm(x0), mm(y0), 0), Pt(mm(x1), mm(y1), 0))


def new_sketch(c):
    return c.sketches.add(c.xYConstructionPlane)


def ext(c, sk, z0, z1, op):
    profs = adsk.core.ObjectCollection.create()
    for p in sk.profiles:
        profs.add(p)
    inp = c.features.extrudeFeatures.createInput(profs, op)
    inp.setDistanceExtent(False, VI(mm(z1 - z0)))
    inp.startExtent = adsk.fusion.OffsetStartDefinition.create(VI(mm(z0)))
    return c.features.extrudeFeatures.add(inp)


def fillet_flat_face(c, body, zmm, r):
    for f in body.faces:
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        bb = f.boundingBox
        if abs(bb.minPoint.z - mm(zmm)) < 1e-4 and abs(bb.maxPoint.z - mm(zmm)) < 1e-4:
            edges = adsk.core.ObjectCollection.create()
            for e in f.edges:
                edges.add(e)
            inp = c.features.filletFeatures.createInput()
            inp.addConstantRadiusEdgeSet(edges, VI(mm(r)), True)
            c.features.filletFeatures.add(inp)
            return
    raise RuntimeError('flat face at z=%s not found' % zmm)


def new_comp(name):
    for o in list(root.occurrences):
        if o.component.name == name:
            o.deleteMe()
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    c = occ.component
    c.name = name
    return c


def window_cuts(c, boxes):
    for (x0, x1, y0, y1, z0, z1) in boxes:
        sk = new_sketch(c)
        rect(sk, x0, x1, y0, y1)
        ext(c, sk, z0, z1, CUT)


def info(c):
    out = []
    for b in c.bRepBodies:
        bb = b.boundingBox
        out.append({'name': b.name, 'vol_cm3': round(b.volume, 2),
                    'bbox_mm': [round(v * 10, 1) for v in (bb.minPoint.x, bb.minPoint.y, bb.minPoint.z,
                                                           bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z)],
                    'faces': b.faces.count, 'valid': b.isValid})
    return out


# ---------------- bezel ----------------
def build_bezel():
    c = new_comp('Bezel')
    sk = new_sketch(c); rrect(sk, xc, yc, outer_w, outer_h, outer_r)
    ext(c, sk, -face_t, zj, NEW)
    body = c.bRepBodies.item(0); body.name = 'Bezel'
    log.append('bezel solid ok')
    fillet_flat_face(c, body, -face_t, front_fillet); log.append('front fillet ok')
    sk = new_sketch(c); rrect(sk, xc, yc, pocket_w, pocket_h, pocket_r)
    ext(c, sk, 0, zj + 0.2, CUT); log.append('pocket ok')
    sk = new_sketch(c)
    rrect(sk, xc + win_dx, yc + win_dy, act_w + 2 * win_margin, act_h + 2 * win_margin, win_r)
    ext(c, sk, -face_t - 0.2, 0.1, CUT); log.append('window ok')
    sk = new_sketch(c); circles(sk, posts, boss_d)
    ext(c, sk, T + boss_gap, zj, JOIN); log.append('bosses ok')
    sk = new_sketch(c); circles(sk, posts, insert_d)
    ext(c, sk, zj - insert_depth, zj + 0.1, CUT); log.append('insert holes ok')
    z0 = T + boss_gap
    window_cuts(c, [
        # left side: display connectors (HDMI/touch/power) and the Raspberry's USB cable
        (xl_out - 1, xl_in + 0.9, y_power - 6, 14.0, z0, zj + 0.1),
        (xl_out - 1, xl_in + 0.9, 14.0, 38.0, z0, zj + 0.1),
        # right side: brightness/volume wheel and headphone jack
        (xr_in - 0.9, xr_out + 1, y_wheel - 9, y_wheel + 9, z0, zj + 0.1),
        (xr_in - 0.9, xr_out + 1, y_jack - 6, y_jack + 6, z0, zj + 0.1),
    ])
    log.append('windows ok')
    return info(c)


# ---------------- shell ----------------
def build_shell():
    c = new_comp('Shell')
    sk = new_sketch(c); rrect(sk, xc, yc, outer_w, outer_h, outer_r)
    ext(c, sk, zj, z_back, NEW)
    body = c.bRepBodies.item(0); body.name = 'Shell'
    log.append('shell solid ok')
    fillet_flat_face(c, body, z_back, back_fillet); log.append('back fillet ok')
    sk = new_sketch(c); rrect(sk, xc, yc, pocket_w, pocket_h, pocket_r)
    ext(c, sk, zj - 0.2, back_in, CUT); log.append('cavity ok')
    sk = new_sketch(c); circles(sk, posts, boss_d)
    ext(c, sk, zj, back_in + 0.1, JOIN); log.append('posts ok')
    sk = new_sketch(c); circles(sk, posts, screw_d)
    ext(c, sk, zj - 0.1, z_back + 0.1, CUT); log.append('screw holes ok')
    sk = new_sketch(c); circles(sk, posts, cbore_d)
    ext(c, sk, z_back - cbore_depth, z_back + 0.1, CUT); log.append('counterbores ok')
    # keyhole slots (large head at the bottom, shank at the top)
    sk = new_sketch(c)
    for sx in (-key_dx, key_dx):
        circles(sk, [(xc + sx, key_y)], key_head)
        rrect(sk, xc + sx, key_y + key_slot_len / 2, key_slot_w, key_slot_len, 2.0)
    ext(c, sk, back_in - 0.1, z_back + 0.1, CUT); log.append('keyholes ok')
    # ventilation above the Raspberry
    sk = new_sketch(c)
    for i in range(vent_n):
        rrect(sk, vent_cx + (i - (vent_n - 1) / 2) * vent_pitch, vent_cy, vent_w, vent_len, 1.0)
    ext(c, sk, back_in - 0.1, z_back + 0.1, CUT); log.append('ventilation ok')
    window_cuts(c, [(xl_out - 1, xl_in + 0.9, 14.0, 38.0, zj - 0.1, 39.0)])
    log.append('cable window ok')
    return info(c)


# ---------------- interference check against the mesh ----------------
def check():
    mb = root.meshBodies.item(0)
    co = mb.displayMesh.nodeCoordinatesAsDouble
    pts = [(co[i], co[i + 1], co[i + 2]) for i in range(0, len(co), 3)]
    res = {}
    for occ in root.occurrences:
        c = occ.component
        if c.name not in ('Bezel', 'Shell') or c.bRepBodies.count == 0:
            continue
        b = c.bRepBodies.item(0)
        bb = b.boundingBox
        hit = []
        for p in pts:
            if p[2] < mm(11.6):          # the display module (z<T) is inside the pocket by definition
                continue
            if not (bb.minPoint.x <= p[0] <= bb.maxPoint.x and bb.minPoint.y <= p[1] <= bb.maxPoint.y
                    and bb.minPoint.z <= p[2] <= bb.maxPoint.z):
                continue
            if b.pointContainment(Pt(p[0], p[1], p[2])) == adsk.fusion.PointContainment.PointInsidePointContainment:
                hit.append(p)
        r = {'nodes_inside': len(hit)}
        if hit:
            r['bbox_mm'] = [round(min(h[k] for h in hit) * 10, 1) for k in range(3)] + \
                           [round(max(h[k] for h in hit) * 10, 1) for k in range(3)]
            r['sample_mm'] = [[round(v * 10, 1) for v in h] for h in hit[:6]]
        res[c.name] = r
    return res


PART = globals().get('PART', 'both')
result = {}
try:
    if PART in ('bezel', 'both'):
        result['bezel'] = build_bezel()
    if PART in ('shell', 'both'):
        result['shell'] = build_shell()
    if PART == 'check':
        result['interference'] = check()
except Exception:
    result['error'] = traceback.format_exc()
result['log'] = log
print(json.dumps(result))

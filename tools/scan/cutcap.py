"""Trim the aligned scan at z = Z0 (keep z >= Z0), snap the cut outline onto the
display spec rectangle and close it with a flat cap built along the loop order.
Keeps UVs so the texture stays."""
import sys, math, json
from collections import defaultdict

SRC, DST = sys.argv[1], sys.argv[2]
Z0 = 3.418
XC, YC, HW, HH = 21.6, 18.2, 164.9 / 2, 102.0 / 2   # spec 164.9 x 102 centred on the case

V, VT, VN, F, keep = [], [], [], [], []
for line in open(SRC):
    t = line.split()
    if not t: continue
    if t[0] == 'v': V.append(tuple(map(float, t[1:4])))
    elif t[0] == 'vt': VT.append(tuple(map(float, t[1:3])))
    elif t[0] == 'vn': VN.append(tuple(map(float, t[1:4])))
    elif t[0] == 'f':
        F.append([tuple((int(x) - 1) if x else None for x in (c.split('/') + ['', ''])[:3]) for c in t[1:]])
    elif t[0] in ('mtllib', 'usemtl', 'g'): keep.append(line.rstrip('\n'))

nv, nvt, nvn = list(V), list(VT), list(VN)
cache = {}
def cut_point(a, b):
    if a[0] > b[0]: a, b = b, a
    pa, pb = V[a[0]], V[b[0]]
    s = (Z0 - pa[2]) / (pb[2] - pa[2])
    pkey = (a[0], b[0])                     # position shared across UV seams
    if pkey not in cache:
        p = tuple(pa[i] + s * (pb[i] - pa[i]) for i in range(3))
        nv.append((p[0], p[1], Z0)); cache[pkey] = len(nv) - 1
    vi = cache[pkey]
    tkey = ('t', a[1], b[1])
    ti = None
    if a[1] is not None and b[1] is not None:
        if tkey not in cache:
            ta, tb = VT[a[1]], VT[b[1]]
            nvt.append(tuple(ta[i] + s * (tb[i] - ta[i]) for i in range(2))); cache[tkey] = len(nvt) - 1
        ti = cache[tkey]
    ni = a[2] if a[2] is not None else b[2]
    return (vi, ti, ni)

out_faces = []
for f in F:
    for k in range(1, len(f) - 1):
        tri = [f[0], f[k], f[k + 1]]
        inside = [V[c[0]][2] >= Z0 for c in tri]
        if all(inside): out_faces.append(tri); continue
        if not any(inside): continue
        poly = []
        for i in range(3):
            c, nx = tri[i], tri[(i + 1) % 3]
            ci, ni_ = inside[i], inside[(i + 1) % 3]
            if ci: poly.append(c)
            if ci != ni_: poly.append(cut_point(c, nx))
        for k2 in range(1, len(poly) - 1):
            out_faces.append([poly[0], poly[k2], poly[k2 + 1]])

# boundary loop on the cut plane, in the order of the wall triangles
edge_set = set()
for tri in out_faces:
    for i in range(3): edge_set.add((tri[i][0], tri[(i + 1) % 3][0]))
bnd = [(a, b) for (a, b) in edge_set if (b, a) not in edge_set
       and abs(nv[a][2] - Z0) < 1e-6 and abs(nv[b][2] - Z0) < 1e-6]
nxt = {a: b for a, b in bnd}
assert len(nxt) == len(bnd), 'boundary vertex with two outgoing edges'
loops, seen = [], set()
for a, _ in bnd:
    if a in seen: continue
    loop, cur = [], a
    while cur not in seen and cur in nxt:
        seen.add(cur); loop.append(cur); cur = nxt[cur]
    loops.append(loop)
loops.sort(key=len, reverse=True)
info = {'faces': len(out_faces), 'loops': [len(l) for l in loops[:10]]}
assert len(loops) == 1, 'cut outline is not a single loop'
main = loops[0]
xs = [nv[i][0] for i in main]; ys = [nv[i][1] for i in main]
info['loop_bbox_before'] = [round(min(xs), 2), round(max(xs), 2), round(min(ys), 2), round(max(ys), 2)]

# snap: the vertex nearest to each rectangle corner goes exactly on the corner,
# every other vertex is projected radially onto the rectangle boundary
corners = [(XC + HW, YC + HH), (XC - HW, YC + HH), (XC - HW, YC - HH), (XC + HW, YC - HH)]
ang = lambda x, y: math.atan2(y - YC, x - XC)
def adiff(a, b):
    d = (a - b + math.pi) % (2 * math.pi) - math.pi
    return abs(d)
corner_vtx = {}
for cx, cy in corners:
    ca = ang(cx, cy)
    best = min(main, key=lambda i: adiff(ang(nv[i][0], nv[i][1]), ca))
    corner_vtx[best] = (cx, cy)
wrap = lambda d: (d + math.pi) % (2 * math.pi) - math.pi
tot = sum(wrap(ang(nv[main[(k + 1) % len(main)]][0], nv[main[(k + 1) % len(main)]][1]) -
               ang(nv[main[k]][0], nv[main[k]][1])) for k in range(len(main)))
dirn = 1 if tot > 0 else -1
info['loop_direction'] = 'CCW' if dirn > 0 else 'CW'
s0 = next(k for k, i in enumerate(main) if i in corner_vtx)
main = main[s0:] + main[:s0]                      # start the walk on a corner
EPS = 1e-4                                         # rad, keeps points distinct
cur = None
maxmove = 0.0
for i in main:
    x, y, _ = nv[i]
    if i in corner_vtx:
        px, py = corner_vtx[i]
        a = ang(px, py)
        if cur is None: cur = a
        else: cur = cur + dirn * max(0.0, dirn * wrap(a - cur))
    else:
        a_raw = ang(x, y)
        cur = cur + dirn * max(EPS, dirn * wrap(a_raw - cur))
        dx, dy = math.cos(cur), math.sin(cur)
        s = 1.0 / max(abs(dx) / HW, abs(dy) / HH)
        px, py = XC + dx * s, YC + dy * s
    maxmove = max(maxmove, math.hypot(px - x, py - y))
    nv[i] = (px, py, Z0)
info['max_snap_mm'] = round(maxmove, 2)
info['corner_vertices'] = len(corner_vtx)

# angular monotonicity check (a fold would make the fan overlap itself)
folds = 0
for k in range(len(main)):
    a0 = ang(nv[main[k]][0], nv[main[k]][1]); a1 = ang(nv[main[(k + 1) % len(main)]][0], nv[main[(k + 1) % len(main)]][1])
    d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    if d < -1e-9: folds += 1
info['angle_folds'] = folds

# cap: fan from the centre along the loop order, normal -Z
uv_glass = None
for tri in out_faces:
    for c in tri:
        if c[1] is not None and abs(nv[c[0]][2] - Z0) < 0.05 and abs(nv[c[0]][0] - XC) < 60 and abs(nv[c[0]][1] - YC) < 30:
            uv_glass = c[1]; break
    if uv_glass is not None: break
if uv_glass is None:
    for tri in out_faces:
        if tri[0][1] is not None: uv_glass = tri[0][1]; break
nv.append((XC, YC, Z0)); ci = len(nv) - 1
nvn.append((0.0, 0.0, -1.0)); cn = len(nvn) - 1
cap = []
for a in main:
    b = nxt[a]
    cap.append([(ci, uv_glass, cn), (b, uv_glass, cn), (a, uv_glass, cn)])   # contains edge (b, a)
info['cap_faces'] = len(cap)

with open(DST, 'w', newline='\n') as g:
    g.write('# scan tagliata a z=%.3f e chiusa con rettangolo %.1f x %.1f (mm)\n' % (Z0, 2 * HW, 2 * HH))
    for l in keep:
        if l.startswith('mtllib'): g.write(l + '\n')
    for p in nv: g.write('v %.5f %.5f %.5f\n' % p)
    for t in nvt: g.write('vt %.6f %.6f\n' % t)
    for n in nvn: g.write('vn %.6f %.6f %.6f\n' % n)
    for l in keep:
        if not l.startswith('mtllib'): g.write(l + '\n')
    def corner(c):
        v, t, n = c
        return '%d/%s/%s' % (v + 1, '' if t is None else t + 1, '' if n is None else n + 1)
    for tri in out_faces + cap:
        g.write('f ' + ' '.join(corner(c) for c in tri) + '\n')
print(json.dumps(info))

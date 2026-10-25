"""Square the display-module walls of the capped scan to the datasheet rectangle.
Per axis, vertices closer than E0 to (or beyond) the rectangle edge are put exactly on it;
the strip [-E1, -E0] is stretched so the mapping stays continuous and monotone.
The effect fades out with z between Z_FULL and Z_FADE."""
import sys, math, json

SRC, DST = sys.argv[1], sys.argv[2]
XC, YC, HW, HH = 21.6, 18.2, 164.9 / 2, 102.0 / 2
E0, E1 = 1.8, 6.0          # mm inside the edge: fully snapped / untouched beyond
EOUT = 5.0                 # mm outside the edge still pulled in
Z_FULL, Z_FADE = 12.4, 14.4

lines = open(SRC).read().split('\n')
V = []
for l in lines:
    if l.startswith('v '): V.append(tuple(map(float, l.split()[1:4])))

faces = [[int(c.split('/')[0]) - 1 for c in l.split()[1:]] for l in lines if l.startswith('f ')]
used = set(i for f in faces for i in f)

def axis_map(d, H):
    """d = signed coordinate relative to the centre; returns the new coordinate."""
    s = 1.0 if d >= 0 else -1.0
    e = abs(d) - H                                   # >0 outside the edge
    if e > EOUT: return d
    if e >= -E0: ne = 0.0
    elif e > -E1: ne = -E1 + (e + E1) * (E1 / (E1 - E0))
    else: return d
    return s * (H + ne)

def weight(z):
    if z <= Z_FULL: return 1.0
    if z >= Z_FADE: return 0.0
    return 1.0 - (z - Z_FULL) / (Z_FADE - Z_FULL)

NV = list(V)
moved, maxmove = 0, 0.0
for i in used:
    x, y, z = V[i]
    w = weight(z)
    if w <= 0: continue
    nx = XC + axis_map(x - XC, HW); ny = YC + axis_map(y - YC, HH)
    nx = x + w * (nx - x); ny = y + w * (ny - y)
    m = math.hypot(nx - x, ny - y)
    if m > 1e-6: moved += 1
    maxmove = max(maxmove, m)
    NV[i] = (nx, ny, z)

def normal(P, f):
    a, b, c = P[f[0]], P[f[1]], P[f[2]]
    u = (b[0]-a[0], b[1]-a[1], b[2]-a[2]); v = (c[0]-a[0], c[1]-a[1], c[2]-a[2])
    return (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
flipped = degenerate = 0
for f in faces:
    n0, n1 = normal(V, f), normal(NV, f)
    l0 = math.sqrt(sum(c*c for c in n0)); l1 = math.sqrt(sum(c*c for c in n1))
    if l1 < 1e-9: degenerate += 1
    elif l0 > 1e-9 and sum(a*b for a, b in zip(n0, n1)) < 0: flipped += 1

out, k = [], 0
for l in lines:
    if l.startswith('v '):
        out.append('v %.5f %.5f %.5f' % NV[k]); k += 1
    else:
        out.append(l)
open(DST, 'w', newline='\n').write('\n'.join(out))
print(json.dumps({'moved': moved, 'max_move_mm': round(maxmove, 2), 'flipped_faces': flipped,
                  'degenerate_faces': degenerate, 'faces': len(faces)}))

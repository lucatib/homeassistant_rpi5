"""Find the rigid transform that maps the raw OBJ scan (meters, Y-up) onto the
submesh currently in Fusion (mm, Z-up). Pure Python: Horn quaternion + grid NN."""
import math, random, sys, json

OBJ = sys.argv[1]
FUS = sys.argv[2]

src = []
with open(OBJ) as f:
    for line in f:
        if line.startswith('v '):
            _, x, y, z = line.split()[:4]
            src.append((float(x) * 1000, float(y) * 1000, float(z) * 1000))
dst = [tuple(map(float, l.split())) for l in open(FUS) if l.strip()]

CELL = 3.0
grid = {}
for p in dst:
    grid.setdefault((int(p[0] // CELL), int(p[1] // CELL), int(p[2] // CELL)), []).append(p)

def nearest(p, rad=2):
    kx, ky, kz = int(p[0] // CELL), int(p[1] // CELL), int(p[2] // CELL)
    best, bd = None, 1e18
    for dx in range(-rad, rad + 1):
        for dy in range(-rad, rad + 1):
            for dz in range(-rad, rad + 1):
                for q in grid.get((kx + dx, ky + dy, kz + dz), ()):
                    d2 = (q[0]-p[0])**2 + (q[1]-p[1])**2 + (q[2]-p[2])**2
                    if d2 < bd: bd, best = d2, q
    return best, bd

def apply(R, t, p):
    return (R[0][0]*p[0]+R[0][1]*p[1]+R[0][2]*p[2]+t[0],
            R[1][0]*p[0]+R[1][1]*p[1]+R[1][2]*p[2]+t[1],
            R[2][0]*p[0]+R[2][1]*p[1]+R[2][2]*p[2]+t[2])

def matmul(A, B):
    return [[sum(A[i][k]*B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

def horn(P, Q):
    n = len(P)
    cp = [sum(p[i] for p in P)/n for i in range(3)]
    cq = [sum(q[i] for q in Q)/n for i in range(3)]
    S = [[0.0]*3 for _ in range(3)]
    for p, q in zip(P, Q):
        a = [p[i]-cp[i] for i in range(3)]; b = [q[i]-cq[i] for i in range(3)]
        for i in range(3):
            for j in range(3): S[i][j] += a[i]*b[j]
    Sxx,Sxy,Sxz = S[0]; Syx,Syy,Syz = S[1]; Szx,Szy,Szz = S[2]
    N = [[Sxx+Syy+Szz, Syz-Szy, Szx-Sxz, Sxy-Syx],
         [Syz-Szy, Sxx-Syy-Szz, Sxy+Syx, Szx+Sxz],
         [Szx-Sxz, Sxy+Syx, -Sxx+Syy-Szz, Syz+Szy],
         [Sxy-Syx, Szx+Sxz, Syz+Szy, -Sxx-Syy+Szz]]
    shift = sum(abs(N[i][j]) for i in range(4) for j in range(4))
    M = [[N[i][j] + (shift if i == j else 0) for j in range(4)] for i in range(4)]
    v = [1.0, 0.1, 0.1, 0.1]
    for _ in range(300):
        w = [sum(M[i][j]*v[j] for j in range(4)) for i in range(4)]
        nrm = math.sqrt(sum(x*x for x in w)); v = [x/nrm for x in w]
    q0,qx,qy,qz = v
    R = [[q0*q0+qx*qx-qy*qy-qz*qz, 2*(qx*qy-q0*qz), 2*(qx*qz+q0*qy)],
         [2*(qy*qx+q0*qz), q0*q0-qx*qx+qy*qy-qz*qz, 2*(qy*qz-q0*qx)],
         [2*(qz*qx-q0*qy), 2*(qz*qy+q0*qx), q0*q0-qx*qx-qy*qy+qz*qz]]
    rcp = apply(R, (0,0,0), cp)
    t = [cq[i]-rcp[i] for i in range(3)]
    return R, t

random.seed(1)
sample = random.sample(src, 2500)

def run(R0):
    # initial translation: align bbox centers in x,y; z by max
    P = [apply(R0, (0,0,0), p) for p in src]
    t0 = [0, 0, 0]
    for i in range(3):
        lo_p, hi_p = min(p[i] for p in P), max(p[i] for p in P)
        lo_q, hi_q = min(q[i] for q in dst), max(q[i] for q in dst)
        t0[i] = (hi_q - hi_p) if i == 2 else ((lo_q+hi_q)/2 - (lo_p+hi_p)/2)
    R, t = R0, t0
    for it in range(40):
        rad = 6 if it < 10 else 2
        pairs = []
        for p in sample:
            tp = apply(R, t, p)
            q, d2 = nearest(tp, rad)
            if q is not None: pairs.append((p, q, d2))
        pairs.sort(key=lambda x: x[2])
        keep = pairs[:int(len(pairs)*0.8)]
        R, t = horn([a for a,_,_ in keep], [b for _,b,_ in keep])
    errs = []
    for p in sample:
        q, d2 = nearest(apply(R, t, p), 2)
        if q is not None: errs.append(math.sqrt(d2))
    errs.sort()
    return R, t, errs[len(errs)//2], len(errs)

best = None
for name, R0 in (('x+90 (x,-z,y)', [[1,0,0],[0,0,-1],[0,1,0]]),
                 ('x+90 flipped (-x,z,y)', [[-1,0,0],[0,0,1],[0,1,0]])):
    R, t, med, cnt = run(R0)
    print(name, 'median err mm', round(med, 3), 'matched', cnt)
    if best is None or med < best[2]: best = (R, t, med, name)
R, t, med, name = best
print(json.dumps({'best': name, 'R': R, 't': t, 'median_mm': med}))

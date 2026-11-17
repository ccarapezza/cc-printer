#!/usr/bin/env python3
"""CC-Printer A1 X/Y steps/mm check: an L of three solid 10x10x7.9 blocks with centres 100 mm
apart in X and in Y, joined by low bars (6 x 1.9 mm) so the piece stays rigid.
Measure per axis A = outside-to-outside (110 nominal) and B = gap between the blocks above the
bar (90 nominal). D = (A+B)/2 is the centre distance: line-width / flow error cancels out.
New steps = current steps x 100 / D.   usage: gen_xy_dim.py [hotend C]"""
import os, struct, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); CAL = os.path.dirname(HERE)
SLICER = os.path.join(CAL, "..", "gcode", "_slicer", "slice_cli.py")
T = int(sys.argv[1]) if len(sys.argv) > 1 else 190
tris = []
def box(x0, x1, y0, y1, z0, z1):
    v = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    c = [(x0+x1)/2, (y0+y1)/2, (z0+z1)/2]
    for a, b, cc, d in [(0,1,3,2), (4,5,7,6), (0,1,5,4), (2,3,7,6), (0,2,6,4), (1,3,7,5)]:
        for f in ((a, b, cc), (a, cc, d)):
            p, q, r = (v[i] for i in f)
            n = [(q[1]-p[1])*(r[2]-p[2]) - (q[2]-p[2])*(r[1]-p[1]),
                 (q[2]-p[2])*(r[0]-p[0]) - (q[0]-p[0])*(r[2]-p[2]),
                 (q[0]-p[0])*(r[1]-p[1]) - (q[1]-p[1])*(r[0]-p[0])]
            m = [(p[i]+q[i]+r[i])/3 - c[i] for i in range(3)]
            tris.append((p, q, r) if sum(n[i]*m[i] for i in range(3)) > 0 else (p, r, q))
H, HB, S, L = 7.9, 1.9, 5.0, 100.0          # block height, bar height, block half-size, centre distance
for cx, cy in ((0, 0), (L, 0), (0, L)):
    box(cx - S, cx + S, cy - S, cy + S, 0, H)
box(S - 0.1, L - S + 0.1, -3, 3, 0, HB)      # X bar
box(-3, 3, S - 0.1, L - S + 0.1, 0, HB)      # Y bar
stl = os.path.join(CAL, "CCPA1_MedidaXY.stl")
out = bytearray(b"CCPA1 control pasos X/Y: bloques a 100 mm".ljust(80, b" ")) + struct.pack("<I", len(tris))
for t in tris:
    out += struct.pack("<3f", 0, 0, 0) + b"".join(struct.pack("<3f", *p) for p in t) + b"\0\0"
open(stl, "wb").write(out)
gc = os.path.join(CAL, f"CCPA1_MedidaXY_{T}.gcode")
title = f"CC-Printer A1 - CONTROL PASOS X/Y: 3 bloques a 100 mm (medir A afuera-afuera y B hueco, D=(A+B)/2), Diario 0.2, {T}C"
r = subprocess.run([sys.executable, SLICER, stl, gc, "1", "base=diario", f"hotend={T}", f"title={title}"],
                   capture_output=True, text=True)
print(r.stdout.strip()); assert r.returncode == 0, r.stderr

#!/usr/bin/env python3
"""CC-Printer A1 temperature tower (PLA), Diario 0.2 profile, generated geometry.
7 blocks of 8 mm, 220 C at the bottom down to 190 C at the top (-5 C per block).
Each block: left pillar 12x12 with the temperature embossed on the front (7-segment digits),
a 14 mm bridge, a middle pillar with a 45 deg overhang on the right, a 55 deg overhang on the
left, and the open window between the pillars shows stringing (travel + retract every layer).
All Z boundaries sit on layer tops (first layer 0.3, then 0.2): 0.9 + 8k + offsets in odd tenths.
usage: gen_temp_tower.py   (writes CCPA1_TorreTemp.stl and CCPA1_TorreTemp_220-190.gcode next to calibracion/)"""
import math, os, re, struct, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); CAL = os.path.dirname(HERE)
SLICER = os.path.join(CAL, "..", "gcode", "_slicer", "slice_cli.py")
TEMPS = [220, 215, 210, 205, 200, 195, 190]
BASE_T, BH = 0.9, 8.0                       # base plate thickness, block height
D = 12.0                                    # depth (Y)
LP = (0.0, 12.0); MP = (26.0, 34.0)         # left / middle pillar X ranges -> 14 mm bridge
WEDGE45 = 8.0                               # 45 deg: 8 mm out over 8 mm
W55_H = 4.0; W55_X = W55_H * math.tan(math.radians(55))   # 55 deg from vertical, top half
SLAB = 1.0                                  # bridge slab thickness
shells = []

def shell(verts, faces):                    # convex shell; fix winding to point outwards
    c = [sum(v[i] for v in verts) / len(verts) for i in range(3)]
    for f in faces:
        a, b, cc = (verts[i] for i in f)
        n = [(b[1]-a[1])*(cc[2]-a[2]) - (b[2]-a[2])*(cc[1]-a[1]),
             (b[2]-a[2])*(cc[0]-a[0]) - (b[0]-a[0])*(cc[2]-a[2]),
             (b[0]-a[0])*(cc[1]-a[1]) - (b[1]-a[1])*(cc[0]-a[0])]
        m = [(a[i]+b[i]+cc[i])/3 - c[i] for i in range(3)]
        shells.append((a, b, cc) if sum(n[i]*m[i] for i in range(3)) > 0 else (a, cc, b))

def box(x0, x1, y0, y1, z0, z1):
    v = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    q = [(0,1,3,2), (4,5,7,6), (0,1,5,4), (2,3,7,6), (0,2,6,4), (1,3,7,5)]
    shell(v, [f for a,b,c,d in q for f in ((a,b,c), (a,c,d))])

def prism_xz(tri, y0, y1):                  # XZ triangle extruded along Y
    v = [(x, y, z) for y in (y0, y1) for (x, z) in tri]
    shell(v, [(0,1,2), (3,4,5), (0,1,4), (0,4,3), (1,2,5), (1,5,4), (2,0,3), (2,3,5)])

SEG = {"0": "abcdef", "1": "bc", "2": "abged", "5": "afgcd", "9": "abcdfg"}
def digit(ch, x0, z0, w=3.0, h=5.6, t=0.8, y0=-0.6, y1=0.3):
    hm = z0 + h / 2
    r = {"a": (x0, x0+w, z0+h-t, z0+h), "d": (x0, x0+w, z0, z0+t), "g": (x0, x0+w, hm-t/2, hm+t/2),
         "f": (x0, x0+t, hm, z0+h), "e": (x0, x0+t, z0, hm), "b": (x0+w-t, x0+w, hm, z0+h), "c": (x0+w-t, x0+w, z0, hm)}
    for s in SEG[ch]:
        xa, xb, za, zb = r[s]; box(xa, xb, y0, y1, za, zb)

box(-3.0, MP[1] + WEDGE45 + 1.0, -3.0, D + 3.0, 0.0, BASE_T)                 # base plate
for k, t in enumerate(TEMPS):
    z0 = BASE_T + BH * k; z1 = z0 + BH
    box(*LP, 0, D, z0, z1)                                                     # left pillar
    box(*MP, 0, D, z0, z1)                                                     # middle pillar
    box(LP[0], MP[1], 0, D, z1 - SLAB, z1)                                     # 14 mm bridge slab
    prism_xz([(MP[1], z0), (MP[1] + WEDGE45, z1), (MP[1], z1)], 0, D)          # 45 deg overhang
    prism_xz([(LP[0], z1 - W55_H), (LP[0], z1), (LP[0] - W55_X, z1)], 0, D)    # 55 deg overhang
    for i, ch in enumerate(str(t)):                                            # 220 ... 190 embossed
        digit(ch, LP[0] + 0.5 + i * 4.0, z0 + 1.0)

stl = os.path.join(CAL, "CCPA1_TorreTemp.stl")
out = bytearray(b"CCPA1 torre de temperatura 220-190".ljust(80, b" ")) + struct.pack("<I", len(shells))
for t in shells:
    out += struct.pack("<3f", 0, 0, 0) + b"".join(struct.pack("<3f", *v) for v in t) + b"\0\0"
open(stl, "wb").write(out)
top = BASE_T + BH * len(TEMPS)
print(f"STL: {len(shells)} triangulos, alto {top:.1f} mm")

gc = os.path.join(CAL, "CCPA1_TorreTemp_220-190.gcode")
title = (f"CC-Printer A1 - TORRE DE TEMPERATURA PLA {TEMPS[0]}->{TEMPS[-1]} C (-5 C cada {BH:.0f} mm, numero en relieve), "
         "perfil Diario 0.2 + modo puente - CuraEngine CLI")
r = subprocess.run([sys.executable, SLICER, stl, gc, "1", "base=diario", f"hotend={TEMPS[0]}", "bridge_settings_enabled=True", f"title={title}"],
                   capture_output=True, text=True)
print(r.stdout.strip()); assert r.returncode == 0, r.stderr

# --- one M104 per block, at the first layer whose top is above the block start ---
g = open(gc).read().split("\n")
assert not [l for l in g if re.match(r"M10[49] ", l) and "S0" not in l and "S160" not in l and f"S{TEMPS[0]}" not in l], \
    "Cura put other temperatures in the body"
res, k, zlayer, pend = [], 1, None, None
for l in g:
    if l.startswith(";LAYER:"):
        pend = len(res)
    m = re.match(r"G[01] .*Z([\d.]+)", l)
    if m and pend is not None:
        z = float(m.group(1)); pend_idx = pend; pend = None
        if k < len(TEMPS) and z > BASE_T + BH * k + 0.01:
            res.insert(pend_idx, f"M104 S{TEMPS[k]} ; torre: bloque {k+1}/{len(TEMPS)} desde z={BASE_T + BH*k:.1f}")
            res.insert(pend_idx + 1, f"M117 Torre {TEMPS[k]}C bloque {k+1}/{len(TEMPS)}")
            k += 1
    res.append(l)
assert k == len(TEMPS), f"solo {k} cambios de temperatura"
i = next(i for i, l in enumerate(res) if l.startswith(";LAYER:0"))
res.insert(i, f"M117 Torre {TEMPS[0]}C bloque 1/{len(TEMPS)}")
open(gc, "w").write("\n".join(res))
print("cambios:", [l for l in res if l.startswith("M104 S") and "torre" in l])

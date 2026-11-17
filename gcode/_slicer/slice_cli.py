#!/usr/bin/env python3
"""Slice N copies of an STL with CuraEngine CLI using the settings Cura's GUI resolved
(base: 'Diario 0.2' slice 16:40; strong-part keys taken from the 03:21 strong slice).
usage: slice_cli.py <stl> <out.gcode> <N> [base=resistente|diario] [hotend=T] [rotx=DEG] [title=TEXT] [setting=value ...]
  base=     'resistente' (default): Diario + strong keys (5 walls, gyroid 50 %, 210 C, fan 50 %)
            'diario': the plain Diario 0.2 profile (2 walls, cubic 20 %, 200 C, fan 100 %)
  hotend=T  print temperature T (all material_*temperature keys + the M109 in the start G-code)
  rotx=90   rotate the part about X before slicing (90 = old Y becomes height)
  title=..  text for header line 2
  k=v       override a Cura setting (global and extruder)"""
import re, struct, subprocess, sys, os, math
STL, OUT, N = sys.argv[1], sys.argv[2], int(sys.argv[3])
ROTX, TITLE, OVR, BASE, HOTEND = 0.0, "", {}, "resistente", None
for a in sys.argv[4:]:
    k, v = a.split("=", 1)
    if k == "rotx": ROTX = float(v)
    elif k == "base": BASE = v; assert v in ("resistente", "diario"), v
    elif k == "hotend": HOTEND = int(v)
    elif k == "title": TITLE = v
    else: OVR[k] = v
GAP = 10.0
HERE = os.path.dirname(os.path.abspath(__file__))
def parse(a):
    a = a.replace("[WARNING]  ", "", 1)
    g, rest = a.split(" -e0 ", 1); e, _ = rest.split(" -g ", 1)
    pat = re.compile(r'-s ([A-Za-z0-9_]+)="(.*?)"(?=\s+-s |\s*$)', re.S)
    return dict(pat.findall(g)), dict(pat.findall(e))
G_strong, E_strong = parse(open(os.path.join(HERE,"base_resistente_0321.args")).read())
G, E = parse(open(os.path.join(HERE,"base_diario_1640.args")).read())
STRONG_KEYS = ["wall_line_count", "infill_pattern", "infill_sparse_density", "infill_line_distance",
    "cross_infill_pocket_size", "bottom_skin_expand_distance", "bottom_skin_preshrink",
    "expand_skins_expand_distance", "skin_preshrink", "top_skin_expand_distance", "top_skin_preshrink",
    "cool_fan_speed", "cool_fan_speed_max", "cool_fan_speed_min",
    "material_break_preparation_temperature", "material_final_print_temperature",
    "material_initial_print_temperature", "material_print_temperature", "material_print_temperature_layer_0"]
if BASE == "resistente":
    for k in STRONG_KEYS:
        E[k] = E_strong[k]
    G["machine_start_gcode"] = G_strong["machine_start_gcode"]      # M109 S210
    assert "M109 S210" in G["machine_start_gcode"]
if HOTEND:
    for k in ("material_print_temperature", "material_print_temperature_layer_0",
              "material_initial_print_temperature", "material_final_print_temperature"):
        G[k] = E[k] = str(HOTEND)
    G["machine_start_gcode"], nsub = re.subn(r"M109 S\d+", f"M109 S{HOTEND}", G["machine_start_gcode"])
    assert nsub == 1, "start G-code must have exactly one M109"
print("perfil:", BASE, "| hotend", HOTEND or re.search(r"M109 S(\d+)", G["machine_start_gcode"]).group(1))
G["time"] = G["date"] = ""
for k, v in OVR.items():
    G[k] = v; E[k] = v
if OVR: print("overrides:", OVR)

# --- N copies stacked along Y, centred on (0,0) (engine adds the bed centre) ---
d = open(STL, "rb").read(); n = struct.unpack("<I", d[80:84])[0]
tris = [struct.unpack("<12f", d[84+i*50:84+i*50+48]) for i in range(n)]
if ROTX:
    c, sn = math.cos(math.radians(ROTX)), math.sin(math.radians(ROTX))
    rot = lambda x, y, z: (x, y*c - z*sn, y*sn + z*c)
    tris = [sum((rot(*t[j:j+3]) for j in (0, 3, 6, 9)), ()) for t in tris]
xs = [t[j] for t in tris for j in (3,6,9)]; ys = [t[j] for t in tris for j in (4,7,10)]; zs = [t[j] for t in tris for j in (5,8,11)]
cx, cy, z0 = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2, min(zs)
h = max(ys)-min(ys); pitch = h + GAP
out = bytearray(80) + struct.pack("<I", n*N)
for k in range(N):
    dy = (k - (N-1)/2) * pitch
    for t in tris:
        v = list(t)
        for j in (3,6,9): v[j] -= cx
        for j in (4,7,10): v[j] += dy - cy
        for j in (5,8,11): v[j] -= z0
        out += struct.pack("<12fH", *v, 0)
comb = os.path.join(HERE, "combined.stl"); open(comb, "wb").write(out)
print(f"{N} copias, pieza {max(xs)-min(xs):.1f} x {h:.1f} x {max(zs)-z0:.1f} mm, bloque Y {N*h+(N-1)*GAP:.1f} mm")

defs = "/usr/share/cura/resources/definitions"
cmd = ["CuraEngine", "slice", "-o", OUT, "-j", f"{defs}/fdmprinter.def.json"]
for k, v in G.items(): cmd += ["-s", f"{k}={v}"]
cmd += ["-e0"]
for k, v in E.items(): cmd += ["-s", f"{k}={v}"]
cmd += ["-g", "-e0", "-l", comb, "-s", "extruder_nr=0"]
env = dict(os.environ, CURA_ENGINE_SEARCH_PATH=f"{defs}:/usr/share/cura/resources/extruders")
r = subprocess.run(cmd, env=env, capture_output=True, text=True)
errs = [l for l in (r.stdout + r.stderr).splitlines() if re.search(r"error|warning|fail", l, re.I) and len(l) < 300 and "Unrecognized data type" not in l]
print("exit", r.returncode); print("\n".join(errs[-15:]))

# --- header: CuraEngine CLI leaves TIME/Filament as placeholders -> real values ---
g = open(OUT).read().split("\n")
elapsed = [float(l.split(":")[1]) for l in g if l.startswith(";TIME_ELAPSED:")]
used, pos, emax, absmode = 0.0, 0.0, 0.0, True    # retract/unretract must not count twice
for l in g:
    if l.startswith("M82"): absmode = True
    elif l.startswith("M83"): absmode = False
    m = re.match(r"G92 .*E([-\d.]+)", l)
    if m: pos = emax = float(m.group(1)); continue
    m = re.match(r"G[01] .*E([-\d.]+)", l)
    if m:
        v = float(m.group(1)); pos = v if absmode else pos + v
        if pos > emax: used += pos - emax; emax = pos
bb, cur = {}, {"X": 0.0, "Y": 0.0, "Z": 0.0}
for l in g:
    if l.startswith(("G0 ", "G1 ")):
        d = dict(re.findall(r"([XYZE])([-\d.]+)", l))
        for k in "XYZ":
            if k in d: cur[k] = float(d[k])
        if "E" in d and ("X" in d or "Y" in d):
            for k in "XYZ":
                lo, hi = bb.get(k, (1e9, -1e9)); bb[k] = (min(lo, cur[k]), max(hi, cur[k]))
for i, l in enumerate(g[:20]):
    m = re.match(r";(MIN|MAX)([XYZ]):", l)
    if m and m.group(2) in bb: g[i] = f";{m.group(1)}{m.group(2)}:{bb[m.group(2)][0 if m.group(1) == 'MIN' else 1]:.3f}"
    if l.startswith(";TIME:") and elapsed: g[i] = f";TIME:{int(elapsed[-1])}"
    if l.startswith(";Filament used:"): g[i] = f";Filament used: {used/1000:.2f}m"
if TITLE: g.insert(1, "; " + TITLE)
open(OUT, "w").write("\n".join(g))
t = int(elapsed[-1]) if elapsed else 0
print(f"tiempo {t//3600}h{t%3600//60:02d}m, filamento {used/1000:.2f} m (~{used/1000*2.98:.0f} g PLA)")

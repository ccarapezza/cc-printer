#!/usr/bin/env python3
"""Prueba de primera capa: 5 cuadrados de 1 capa (centro + 4 esquinas junto a los tornillos de la cama).
Mientras imprime, ajustar Z en vivo desde Fluidd (SET_GCODE_OFFSET Z_ADJUST=... MOVE=1).
uso: gen_first_layer.py <out.gcode> [T_hotend=200] [T_cama=60]"""
import math, sys
OUT = sys.argv[1]
T = int(sys.argv[2]) if len(sys.argv) > 2 else 200
TB = int(sys.argv[3]) if len(sys.argv) > 3 else 60
LH, W, SIDE = 0.2, 0.45, 25.0                    # altura de capa, ancho de linea, lado del cuadrado
E_MM = ((W - LH) * LH + math.pi * (LH / 2) ** 2) / (math.pi * 0.875 ** 2)   # modelo "estadio": 0.03385
F_PRINT, F_TRAVEL, F_Z = 20 * 60, 60 * 60, 5 * 60
SQUARES = [((100, 100), "1/5 Centro"), ((30, 30), "2/5 Adel izq"), ((170, 30), "3/5 Adel der"),
           ((170, 170), "4/5 Atras der"), ((30, 170), "5/5 Atras izq")]

g, t_print = [], 0.0
def ext(x0, y0, x1, y1):
    global t_print
    d = math.hypot(x1 - x0, y1 - y0); t_print += d / (F_PRINT / 60)
    return d * E_MM

for (cx, cy), name in SQUARES:
    h = SIDE / 2
    x0, y0, x1, y1 = cx - h, cy - h, cx + h, cy + h
    g += [f"M117 {name}", f"G1 Z1.0 F{F_Z}", f"G0 X{x0:.3f} Y{y0:.3f} F{F_TRAVEL}", f"G1 Z{LH} F{F_Z}",
          "G92 E0", "G1 E2 F1500 ; recupera la retraccion"]
    e = 0.0
    # perimetro
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        e += ext(ax, ay, bx, by); g.append(f"G1 X{bx:.3f} Y{by:.3f} E{2 + e:.5f} F{F_PRINT}")
    # relleno en zigzag a lo largo de X, dentro del perimetro
    xa, xb = x0 + W, x1 - W
    y, k = y0 + W, 0
    g.append(f"G0 X{xa:.3f} Y{y:.3f} F{F_TRAVEL}")
    cur = (xa, y)
    while y <= y1 - W + 1e-6:
        tx = xb if k % 2 == 0 else xa
        e += ext(cur[0], cur[1], tx, y); g.append(f"G1 X{tx:.3f} Y{y:.3f} E{2 + e:.5f} F{F_PRINT}")
        cur = (tx, y); y += W; k += 1
        if y <= y1 - W + 1e-6:
            e += ext(cur[0], cur[1], cur[0], y); g.append(f"G1 X{cur[0]:.3f} Y{y:.3f} E{2 + e:.5f} F{F_PRINT}")
            cur = (cur[0], y)
    g.append(f"G1 E{2 + e - 2:.5f} F1500 ; retrae 2 mm")

head = [";FLAVOR:Marlin",
        f"; CC-Printer A1 - PRUEBA DE PRIMERA CAPA: 5 cuadrados de {SIDE:.0f} mm, 1 capa de {LH} mm, {T}C / cama {TB}C",
        "; Ajustar Z en vivo desde Fluidd mientras imprime; despues Z_OFFSET_APPLY_ENDSTOP + SAVE_CONFIG (sin imprimir)",
        f";TIME:{int(t_print + 240)}", f";Layer height: {LH}", ";MINX:3.000", ";MINY:17.500", f";MINZ:{LH}",
        ";MAXX:182.500", ";MAXY:182.500", f";MAXZ:{LH}", "",
        "M220 S100", "M221 S100", "G90", "M82", "M107 ; ventilador apagado en toda la prueba",
        f"M140 S{TB} ; empieza a calentar la cama", "M104 S160 ; precalienta el hotend sin que gotee",
        "G28 ; home X Y Z", "G1 Z10 F600",
        f"M190 S{TB} ; espera la cama", f"M109 S{T} ; espera el hotend",
        "G92 E0", "G1 X3 Y20 Z0.3 F2400 ; linea de purga en el borde izquierdo", "G1 X3 Y180 Z0.3 F1200 E12",
        "G1 X3.5 Y180 Z0.3 F2400", "G1 X3.5 Y20 Z0.3 F1200 E24", "G92 E0", "G1 E-2 F1500 ; retrae", "G92 E0",
        ";LAYER_COUNT:1", ";LAYER:0"]
tail = ["G91", "G1 Z10 F600 ; sube la boquilla", "G90", "G1 X0 Y190 F2400 ; trae la cama hacia adelante",
        "M104 S0", "M140 S0", "M107", "M84", "M117 Primera capa OK?", ";End of Gcode"]
open(OUT, "w").write("\n".join(head + g + tail) + "\n")
print(f"{OUT}: {len(g)} lineas de movimiento, impresion ~{t_print/60:.1f} min + calentar, E/mm {E_MM:.5f}")

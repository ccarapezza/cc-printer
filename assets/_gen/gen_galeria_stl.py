#!/usr/bin/env python3
"""CC-Printer A1: galerías PNG de los STL del repo (para el README).

Renderiza cada STL en vista isométrica con sombreado plano (solo numpy + matplotlib,
sin OpenGL) y arma una lámina por carpeta de stl-repuestos/, otra con las piezas de
calibración y un banner con piezas destacadas.

uso (desde la raíz del repo):  python3 assets/_gen/gen_galeria_stl.py
salida: assets/stl/*.png y assets/banner.png
"""
import glob
import os
import struct
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "assets")
BG, CARD, INK, MUTED = "#f6f8fa", "#ffffff", "#1f2328", "#59636e"

# Un color de "filamento" por lámina
COLORES = {
    "01": "#e8833a", "02": "#3a86e8", "03": "#d64545", "04": "#4caf7a",
    "05": "#8e6bd8", "06": "#d9a21b", "07": "#2fa7b5", "calibracion": "#e0567a",
}


def cargar_stl(ruta):
    """Devuelve un array (n, 3, 3) con los triángulos (STL ASCII o binario)."""
    datos = open(ruta, "rb").read()
    if datos[:5] == b"solid" and b"facet" in datos[:2000]:
        v = [list(map(float, l.split()[1:4])) for l in datos.decode(errors="ignore").splitlines()
             if l.strip().startswith("vertex")]
        return np.array(v, dtype=np.float32).reshape(-1, 3, 3)
    n = struct.unpack("<I", datos[80:84])[0]
    reg = np.frombuffer(datos[84:84 + 50 * n], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    return reg["v"].astype(np.float32)


def rotacion(az=-35.0, el=28.0):
    a, e = np.radians(az), np.radians(el)
    rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    # vista desde -Y hacia +Y, con Z arriba: (x, z) en pantalla, y = profundidad
    return rx @ rz


def dibujar(ax, tri, color):
    tri = tri - tri.reshape(-1, 3).mean(axis=0)
    t = tri @ rotacion().T
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    largo = np.linalg.norm(n, axis=1)
    ok = largo > 1e-12
    t, n = t[ok], n[ok] / largo[ok, None]
    luz = np.array([-0.45, -0.75, 0.55]); luz /= np.linalg.norm(luz)
    k = 0.38 + 0.62 * np.abs(n @ luz)                       # doble cara: normales invertidas no quedan negras
    base = np.array(matplotlib.colors.to_rgb(color))
    caras = np.clip(base[None, :] * k[:, None] + 0.10 * (1 - k[:, None]), 0, 1)
    orden = np.argsort(-t[:, :, 1].mean(axis=1))            # pintor: lo más lejano primero
    pol = t[orden][:, :, [0, 2]]
    ax.add_collection(PolyCollection(pol, facecolors=caras[orden], edgecolors=caras[orden],
                                     linewidths=0.25, antialiased=True))
    xy = pol.reshape(-1, 2)
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    c, r = (lo + hi) / 2, (hi - lo).max() / 2 * 1.08
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_aspect("equal"); ax.axis("off")
    return (hi - lo) / 1.0


def medidas(tri):
    p = tri.reshape(-1, 3)
    return p.max(axis=0) - p.min(axis=0)


def lamina(archivos, titulo, color, salida, cols=5):
    filas = (len(archivos) + cols - 1) // cols
    fig = plt.figure(figsize=(cols * 2.6, filas * 2.75 + 0.75), dpi=110, facecolor=BG)
    fig.text(0.012, 1 - 0.32 / (filas * 2.75 + 0.75), titulo, fontsize=15, weight="bold", color=INK, va="center")
    alto_tit = 0.75 / (filas * 2.75 + 0.75)
    for i, f in enumerate(archivos):
        fi, co = divmod(i, cols)
        w, h = 1 / cols, (1 - alto_tit) / filas
        x0, y0 = co * w, 1 - alto_tit - (fi + 1) * h
        fondo = fig.add_axes([x0 + 0.006, y0 + 0.006, w - 0.012, h - 0.012])
        fondo.set_facecolor(CARD); fondo.set_xticks([]); fondo.set_yticks([])
        for s in fondo.spines.values():
            s.set_color("#d1d9e0")
        ax = fig.add_axes([x0 + 0.02, y0 + h * 0.22, w - 0.04, h * 0.72])
        tri = cargar_stl(f)
        dibujar(ax, tri, color)
        nombre = os.path.splitext(os.path.basename(f))[0]
        if len(nombre) > 30:
            nombre = nombre[:28] + "…"
        mx, my, mz = medidas(tri)
        fig.text(x0 + w / 2, y0 + h * 0.13, nombre, ha="center", fontsize=8.6, color=INK, weight="bold")
        fig.text(x0 + w / 2, y0 + h * 0.055, f"{mx:.0f} × {my:.0f} × {mz:.0f} mm", ha="center", fontsize=7.6, color=MUTED)
    fig.savefig(salida, facecolor=BG)
    plt.close(fig)
    print(f"{salida}  ({len(archivos)} piezas, {os.path.getsize(salida) // 1024} KB)")


def banner(archivos, salida):
    fig = plt.figure(figsize=(13, 2.4), dpi=110, facecolor=BG)
    fig.text(0.015, 0.68, "CC-Printer A1", fontsize=30, weight="bold", color=INK)
    fig.text(0.015, 0.42, "Anet A8 → AM8 metal · TMC2208 · Klipper", fontsize=12.5, color=MUTED)
    fig.text(0.015, 0.26, "firmware, Raspberry Pi y repuestos imprimibles", fontsize=12.5, color=MUTED)
    colores = list(COLORES.values())
    n = len(archivos)
    for i, f in enumerate(archivos):
        ax = fig.add_axes([0.35 + i * (0.645 / n), 0.03, 0.645 / n, 0.94])
        dibujar(ax, cargar_stl(f), colores[i % len(colores)])
    fig.savefig(salida, facecolor=BG)
    plt.close(fig)
    print(f"{salida}  ({os.path.getsize(salida) // 1024} KB)")


def main():
    os.makedirs(os.path.join(OUT, "stl"), exist_ok=True)
    stl = lambda patron: sorted(glob.glob(os.path.join(ROOT, patron), recursive=True), key=str.lower)
    for carpeta in sorted(glob.glob(os.path.join(ROOT, "stl-repuestos", "[0-9][0-9]-*"))):
        nombre = os.path.basename(carpeta)
        archivos = stl(os.path.join("stl-repuestos", nombre, "**", "*.[sS][tT][lL]"))
        titulo = nombre[3:].replace("-", " ")
        titulo = titulo[0].upper() + titulo[1:]
        lamina(archivos, f"{nombre[:2]} · {titulo}", COLORES.get(nombre[:2], "#888888"),
               os.path.join(OUT, "stl", f"{nombre}.png"))
    lamina(stl("calibracion/*.stl"), "Piezas de calibración generadas (calibracion/)",
           COLORES["calibracion"], os.path.join(OUT, "stl", "calibracion.png"), cols=3)
    destacadas = ["stl-repuestos/03-carro-hotend-E3D/Anet_A8_Direct_Feed_E3d_Carriage_Mount_V2.STL",
                  "stl-repuestos/01-marco-AM8HD-ejes-Y-Z/y_brace_v3.stl",
                  "stl-repuestos/02-eje-X-soportes-AM8/AM8_X_Axis_Holders_Motor.stl",
                  "calibracion/CCPA1_TorreTemp.stl",
                  "stl-repuestos/05-electronica-y-pantalla/caja-pantalla-LCD12864/lcd_case.stl"]
    banner([os.path.join(ROOT, d) for d in destacadas], os.path.join(OUT, "banner.png"))


if __name__ == "__main__":
    sys.exit(main())

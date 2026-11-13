#!/usr/bin/env python3
"""Plot the adsb.lol (ODbL 1.0) East-Asia coverage grid made by globe_grid.py: distinct aircraft per 1° cell for one
day, with ZSSS and the 150 km scan circle marked. Usage: python3 -I coverage_map.py GRID_JSON OUT_PNG"""
import json, math, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm

d = json.load(open(sys.argv[1])); g = d["grid"]
A = np.zeros((35, 50)); G = np.zeros((35, 50))
for k, v in g.items():
    la, lo = map(int, k.split(",")); A[la - 15, lo - 95] = v[0]; G[la - 15, lo - 95] = v[2]
fig, ax = plt.subplots(figsize=(9, 6.4), dpi=150)
m = ax.imshow(np.where(A > 0, A, np.nan), origin="lower", extent=[95, 145, 15, 50], cmap="viridis", norm=LogNorm(1, A.max()))
gy, gx = np.nonzero(G)
ax.scatter(gx + 95.5, gy + 15.5, s=8, c="red", marker="s", label="cell with ≥1 aircraft reported on the ground")
ax.plot(121.33426, 31.198104, marker="*", ms=14, mec="k", mfc="orange", label="ZSSS Hongqiao")
t = np.linspace(0, 2 * math.pi, 200)
ax.plot(121.33426 + 150 / 111.2 / math.cos(math.radians(31.2)) * np.cos(t), 31.198104 + 150 / 111.2 * np.sin(t), "w--", lw=1,
        label="150 km around ZSSS: 0 aircraft all day")
ax.set_xlim(100, 140); ax.set_ylim(18, 45); ax.set_xlabel("longitude °E"); ax.set_ylabel("latitude °N")
ax.set_facecolor("#20242a"); ax.grid(color="#555", lw=0.3)
ax.set_title(f"adsb.lol coverage, {d['date']} UTC day: distinct aircraft per 1° cell\n"
             "Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL", fontsize=9)
plt.colorbar(m, ax=ax, label="distinct aircraft (log)"); ax.legend(loc="lower right", fontsize=7)
plt.tight_layout(); plt.savefig(sys.argv[2])

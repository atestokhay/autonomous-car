"""CSV logunu çizer: hedef/rampa/ölçülen hız ve duty."""
import csv
import sys
from collections import defaultdict

import matplotlib.pyplot as plt

rows = list(csv.DictReader(open(sys.argv[1])))
by = defaultdict(list)
for r in rows:
    by[r["side"]].append(r)

fig, axes = plt.subplots(len(by), 2, figsize=(11, 3.5 * len(by)), squeeze=False)
for i, (side, rs) in enumerate(by.items()):
    t = [float(r["t"]) for r in rs]
    axes[i][0].plot(t, [float(r["target"]) for r in rs], "--", label="hedef")
    axes[i][0].plot(t, [float(r["setpoint"]) for r in rs], label="rampa")
    axes[i][0].plot(t, [float(r["speed"]) for r in rs], label="ölçülen")
    axes[i][0].set_title(f"{side}: hız (rad/s)")
    axes[i][0].legend()
    axes[i][1].plot(t, [float(r["duty"]) for r in rs])
    axes[i][1].set_title(f"{side}: duty")
plt.tight_layout()
plt.show()

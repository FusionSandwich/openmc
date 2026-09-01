"""Plot exact C0 coil-control throughput and raw spread."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parents[3]
raw = root / "dev/stellarcsg/benchmarks/raw/composite_blanket_interop/c0_coil_controls.json"
data = json.loads(raw.read_text())
labels = ["built-in\nZTorus", "swept exact\nshared kernel", "swept\nforced-general"]
cases = data["cases"]
medians = [case["median_histories_per_s"] for case in cases]
ratios = [case["ratio_to_builtin"] for case in cases]
figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.5), constrained_layout=True)
axes[0].bar(labels, medians, color=["0.45", "tab:blue", "tab:orange"])
for x, case in enumerate(cases):
    values = case["raw_histories_per_s"]
    axes[0].scatter(np.full(len(values), x), values, color="black", s=14, zorder=3)
axes[0].set_ylabel("histories/s")
axes[0].set_title("1,000,000 histories × 7; CPU 2; 1 thread")
axes[1].bar(labels, ratios, color=["0.45", "tab:blue", "tab:orange"])
axes[1].axhline(0.95, color="tab:green", ls="--", lw=1, label="exact gate 0.95")
axes[1].axhline(0.75, color="tab:red", ls=":", lw=1, label="general preferred 0.75")
axes[1].set_ylabel("throughput / built-in ZTorus")
axes[1].legend(fontsize=8)
figure.suptitle("C0 planar circular coil: exact shape and source\n"
                "c0290b lineage; OpenMC OBB-linked binary; randomized order; zero lost particles")
out = root / "dev/stellarcsg/plots/composite_blanket_interop/c0_coil_throughput.png"
figure.savefig(out, dpi=180)
plt.close(figure)

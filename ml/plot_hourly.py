"""
วาดกราฟเส้นค่าเฉลี่ยจำนวนคนรายชั่วโมง (วันธรรมดา vs เสาร์-อาทิตย์) ของทุกยิม ใช้ใส่สไลด์
ใช้: python ml/plot_hourly.py   (รันจากโฟลเดอร์รากของโปรเจกต์)
ผลลัพธ์: results/hourly_curves.png
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # ไม่ต้องเปิดหน้าต่าง บันทึกเป็นไฟล์อย่างเดียว
import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv("data/occupancy.csv")
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)

for ax, (is_we, title) in zip(axes, [(0, "Weekday"), (1, "Weekend")]):
    sub = df[df.is_weekend == is_we]
    curves = sub.groupby(["gym_name", "hour"])["occupancy_pct"].mean().unstack(0)
    curves.plot(ax=ax, marker="o", markersize=3)
    ax.set_title(f"Average occupancy by hour - {title}")
    ax.set_xlabel("Hour of day")
    ax.set_xticks(range(0, 24, 2))
    ax.grid(alpha=0.3)
axes[0].set_ylabel("Occupancy (% of capacity)")
axes[1].legend(fontsize=8)

Path("results").mkdir(exist_ok=True)
plt.tight_layout()
plt.savefig("results/hourly_curves.png", dpi=150)
print("บันทึกแล้ว: results/hourly_curves.png")
"""
ปรับค่า ASPECT_THRESHOLD อย่างซื่อสัตย์ (ฝั่ง A)
แบ่งชุดเขียนมือเป็น 2 ครึ่ง เลือก threshold จากครึ่งหนึ่ง แล้ววัดผลบนอีกครึ่ง
รัน (จากโฟลเดอร์รากโปรเจกต์):  python ml/tune_threshold.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

from ml.sentiment import ROOT, _read, _split_aspects, _vec

GRID = [round(x, 2) for x in np.arange(0.20, 0.81, 0.05)]

train_df = _read(ROOT / "data" / "reviews_synthetic.csv")
test_df = _read(ROOT / "data" / "reviews_manual.csv")
vec = _vec()
X_tr = vec.fit_transform(train_df["text"])
X_te = vec.transform(test_df["text"])
mlb = MultiLabelBinarizer()
Y_tr = mlb.fit_transform(train_df["aspects"].map(_split_aspects))
asp = OneVsRestClassifier(LogisticRegression(max_iter=2000, class_weight="balanced")).fit(X_tr, Y_tr)
Y_te = mlb.transform(test_df["aspects"].map(_split_aspects))
P = asp.predict_proba(X_te)


def f1_at(idx, t):
    return f1_score(Y_te[idx], (P[idx] >= t).astype(int), average="micro", zero_division=0)


allidx = np.arange(len(test_df))
print("threshold | Micro-F1 (ทั้งชุด)")
for t in GRID:
    print(f"  {t:.2f}    | {f1_at(allidx, t):.3f}")

rng = np.random.RandomState(0)
perm = rng.permutation(len(test_df))
half = len(perm) // 2
A, B = perm[:half], perm[half:]
print("\n== ตรวจแบบแบ่งครึ่ง (เลือกจากครึ่งหนึ่ง วัดบนอีกครึ่ง) ==")
scores = []
for name, tune, hold in [("A->B", A, B), ("B->A", B, A)]:
    best = max(GRID, key=lambda t: f1_at(tune, t))
    s_old, s_new = f1_at(hold, 0.35), f1_at(hold, best)
    scores.append((s_old, s_new))
    print(f"{name}: เลือก threshold={best:.2f} | วัดบนครึ่งที่ไม่ได้ใช้เลือก: 0.35 -> {s_old:.3f}, {best:.2f} -> {s_new:.3f}")
print(f"เฉลี่ย: 0.35 -> {np.mean([s[0] for s in scores]):.3f} | ค่าที่เลือก -> {np.mean([s[1] for s in scores]):.3f}")
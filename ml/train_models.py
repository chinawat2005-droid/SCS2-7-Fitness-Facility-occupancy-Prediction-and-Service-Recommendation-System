"""
ฝึกและเปรียบเทียบ 3 โมเดลพยากรณ์จำนวนคนในยิม
ใช้: python ml/train_models.py   (รันจากโฟลเดอร์รากของโปรเจกต์ หลังรัน gen_occupancy_data.py)

ผลลัพธ์:
  results/model_comparison.csv   ตาราง MAE / RMSE (ใส่สไลด์ได้)
  results/predictions_test.csv   ค่าจริง vs ค่าทำนายของชุดทดสอบ
  models/best_model.joblib       โมเดลที่ RMSE ต่ำสุด + รายชื่อฟีเจอร์
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:  # ถ้าไม่มี xgboost ใช้ GradientBoosting แทน (บอกในสไลด์ให้ตรง)
    from sklearn.ensemble import GradientBoostingRegressor
    HAS_XGB = False

TEST_DAYS = 14
FEATURES = ["gym_id", "hour", "day_of_week", "is_weekend", "is_holiday", "is_exam_period"]


def make_X(df, columns=None):
    X = pd.get_dummies(df[FEATURES], columns=["gym_id"], dtype=int)
    if columns is not None:
        X = X.reindex(columns=columns, fill_value=0)
    return X


def main():
    df = pd.read_csv("data/occupancy.csv", parse_dates=["datetime"])
    cutoff = df["datetime"].max().normalize() - pd.Timedelta(days=TEST_DAYS - 1)
    train, test = df[df["datetime"] < cutoff], df[df["datetime"] >= cutoff]

    X_train = make_X(train)
    X_test = make_X(test, X_train.columns)
    y_train, y_test = train["count"], test["count"]

    if HAS_XGB:
        boosted = ("XGBoost", XGBRegressor(n_estimators=300, max_depth=5, learning_rate=0.05,
                                           random_state=0, n_jobs=-1))
    else:
        boosted = ("GradientBoosting (แทน XGBoost)",
                   GradientBoostingRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                                             random_state=0))
    models = [
        ("LinearRegression", LinearRegression()),
        ("RandomForest", RandomForestRegressor(n_estimators=300, min_samples_leaf=2,
                                               random_state=0, n_jobs=-1)),
        boosted,
    ]

    rows, preds = [], test[["gym_id", "datetime", "count", "capacity"]].copy()
    fitted = {}
    for name, model in models:
        model.fit(X_train, y_train)
        p = np.clip(model.predict(X_test), 0, test["capacity"].to_numpy())
        preds[name] = p.round(1)
        rows.append({
            "model": name,
            "MAE": round(mean_absolute_error(y_test, p), 2),
            "RMSE": round(mean_squared_error(y_test, p) ** 0.5, 2),
        })
        fitted[name] = model

    result = pd.DataFrame(rows).sort_values("RMSE").reset_index(drop=True)
    print(f"train={len(train)} test={len(test)} (test เริ่ม {cutoff.date()})")
    print(result.to_string(index=False))

    Path("results").mkdir(exist_ok=True)
    Path("models").mkdir(exist_ok=True)
    result.to_csv("results/model_comparison.csv", index=False)
    preds.to_csv("results/predictions_test.csv", index=False)

    best = result.loc[0, "model"]
    joblib.dump({"model": fitted[best], "columns": list(X_train.columns), "name": best},
                "models/best_model.joblib")
    print(f"บันทึกโมเดลที่ดีที่สุด: {best}")


if __name__ == "__main__":
    main()
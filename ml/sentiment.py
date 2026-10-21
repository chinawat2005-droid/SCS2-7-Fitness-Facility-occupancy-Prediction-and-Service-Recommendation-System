"""
โมดูลวิเคราะห์รีวิวภาษาไทย (ฝั่ง A): Sentiment (pos/neu/neg) + ประเด็นที่พูดถึง (aspects)

ฝึกและวัดผล (รันจากโฟลเดอร์รากของโปรเจกต์):
    python ml/sentiment.py

ใช้ในโค้ดอื่น (หลังฝึกแล้ว):
    from ml.sentiment import analyze_review
    analyze_review("แอร์เย็นแต่ห้องน้ำสกปรก")
    # {'sentiment': 'neu', 'confidence': 0.6, 'aspects': ['air_conditioning', 'cleanliness']}

ฝึกด้วย data/reviews_synthetic.csv (เทมเพลต) ทดสอบด้วย data/reviews_manual.csv (เขียนและตรวจป้ายด้วยมือ)
"""
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "sentiment.joblib"
LABELS = ["neg", "neu", "pos"]
ASPECT_THRESHOLD = 0.50  # ความน่าจะเป็นขั้นต่ำที่ถือว่า "พูดถึงประเด็นนี้"


def _read(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["text"] = df["text"].astype(str)
    df["aspects"] = df["aspects"].fillna("").astype(str)
    return df


def _split_aspects(s):
    return [a for a in s.split(";") if a]


def _vec():
    return TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)


def train():
    train_df = _read(ROOT / "data" / "reviews_synthetic.csv")
    test_df = _read(ROOT / "data" / "reviews_manual.csv")

    vec = _vec()
    X_train = vec.fit_transform(train_df["text"])
    X_test = vec.transform(test_df["text"])

    # 1) Sentiment
    clf = LogisticRegression(max_iter=2000, class_weight="balanced")
    clf.fit(X_train, train_df["sentiment"])
    pred = clf.predict(X_test)

    lines = []
    lines.append(f"ชุดฝึก (เทมเพลต) {len(train_df)} รีวิว | ชุดทดสอบ (เขียนมือ) {len(test_df)} รีวิว")
    lines.append("")
    lines.append("== Sentiment ==")
    lines.append(classification_report(test_df["sentiment"], pred, labels=LABELS, digits=3, zero_division=0))
    macro = f1_score(test_df["sentiment"], pred, labels=LABELS, average="macro", zero_division=0)
    lines.append(f"Macro-F1 = {macro:.3f}")
    lines.append("Confusion matrix (แถว=จริง, คอลัมน์=ทำนาย, ลำดับ neg neu pos):")
    lines.append(str(confusion_matrix(test_df["sentiment"], pred, labels=LABELS)))

    # 2) Aspects (หลายป้ายต่อรีวิว)
    mlb = MultiLabelBinarizer()
    Y_train = mlb.fit_transform(train_df["aspects"].map(_split_aspects))
    asp = OneVsRestClassifier(LogisticRegression(max_iter=2000, class_weight="balanced"))
    asp.fit(X_train, Y_train)

    Y_test = mlb.transform(test_df["aspects"].map(_split_aspects))
    Y_pred = (asp.predict_proba(X_test) >= ASPECT_THRESHOLD).astype(int)
    micro = f1_score(Y_test, Y_pred, average="micro", zero_division=0)
    lines.append("")
    lines.append("== Aspects (ประเด็นที่พูดถึง) ==")
    lines.append(classification_report(Y_test, Y_pred, target_names=list(mlb.classes_), digits=3, zero_division=0))
    lines.append(f"Micro-F1 = {micro:.3f}")

    # รายการที่ทายผิด (ไว้ดูว่าโมเดลพลาดตรงไหน)
    wrong = test_df[pred != test_df["sentiment"]].copy()
    wrong["predicted"] = pred[pred != test_df["sentiment"]]
    lines.append("")
    lines.append(f"== รีวิวที่ทาย sentiment ผิด ({len(wrong)} รายการ) ==")
    for _, r in wrong.iterrows():
        lines.append(f"- {r['text']} | จริง={r['sentiment']} ทาย={r['predicted']}")

    report = "\n".join(lines)
    print(report)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "sentiment_report.txt").write_text(report, encoding="utf-8")

    # ฝึกซ้ำด้วยข้อมูลทั้งสองชุดก่อนบันทึก เพื่อให้โมเดลที่ใช้งานเห็นภาษาจริงด้วย
    all_df = pd.concat([train_df, test_df], ignore_index=True)
    vec2 = _vec()
    X_all = vec2.fit_transform(all_df["text"])
    clf2 = LogisticRegression(max_iter=2000, class_weight="balanced").fit(X_all, all_df["sentiment"])
    mlb2 = MultiLabelBinarizer()
    Y_all = mlb2.fit_transform(all_df["aspects"].map(_split_aspects))
    asp2 = OneVsRestClassifier(LogisticRegression(max_iter=2000, class_weight="balanced")).fit(X_all, Y_all)

    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump({"vec": vec2, "clf": clf2, "asp": asp2, "mlb": mlb2}, MODEL_PATH)
    print(f"\nบันทึกโมเดล -> {MODEL_PATH}")


_cache = {}


def analyze_review(text):
    """คืน {'sentiment', 'confidence', 'aspects'} ของรีวิว 1 ข้อความ"""
    if "m" not in _cache:
        if not MODEL_PATH.exists():
            raise FileNotFoundError("ยังไม่มีโมเดล ให้รัน python ml/sentiment.py ก่อน")
        _cache["m"] = joblib.load(MODEL_PATH)
    m = _cache["m"]
    X = m["vec"].transform([text])
    proba = m["clf"].predict_proba(X)[0]
    i = proba.argmax()
    ap = m["asp"].predict_proba(X)[0]
    aspects = [c for c, p in zip(m["mlb"].classes_, ap) if p >= ASPECT_THRESHOLD]
    return {"sentiment": str(m["clf"].classes_[i]), "confidence": round(float(proba[i]), 3), "aspects": aspects}


if __name__ == "__main__":
    train()
    print("\n--- ลองวิเคราะห์ ---")
    for t in ["แอร์เย็นสบาย พนักงานน่ารักมาก", "ห้องน้ำสกปรก ราคาแพงด้วย ไม่แนะนำ", "แอร์เย็นแต่ห้องน้ำสกปรก"]:
        print(t, "->", analyze_review(t))
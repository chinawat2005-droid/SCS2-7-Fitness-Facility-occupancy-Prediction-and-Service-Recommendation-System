import datetime as dt
import random
from pathlib import Path

import pandas as pd

from gen_reviews import ASPECTS, CONTRAST, ENDS, SAME, SUFFIX

SEED = 11
PER_GYM = 40
END = dt.datetime(2026, 10, 20, 21, 0)
DAYS = 60
DEFAULT = (0.40, 0.30, 0.30)  # pos, neg, neu
PROFILES = {
    1: {"equipment": (0.70, 0.15, 0.15), "crowding": (0.15, 0.65, 0.20), "price": (0.30, 0.35, 0.35)},
    2: {"equipment": (0.65, 0.15, 0.20), "cleanliness": (0.65, 0.15, 0.20),
        "crowding": (0.15, 0.65, 0.20), "price": (0.15, 0.60, 0.25)},
    3: {"equipment": (0.65, 0.15, 0.20), "staff": (0.65, 0.15, 0.20), "price": (0.60, 0.15, 0.25),
        "crowding": (0.40, 0.20, 0.40)},
    4: {"price": (0.65, 0.10, 0.25), "crowding": (0.15, 0.60, 0.25), "air_conditioning": (0.20, 0.55, 0.25),
        "equipment": (0.25, 0.40, 0.35)},
    5: {"cleanliness": (0.15, 0.60, 0.25), "price": (0.60, 0.15, 0.25), "equipment": (0.20, 0.55, 0.25),
        "air_conditioning": (0.15, 0.55, 0.30)},
}
ASPECT_ORDER = list(ASPECTS)


def build(rng, gym_id):
    prof = PROFILES[gym_id]
    n = rng.choices([1, 2, 3], [0.40, 0.45, 0.15])[0]
    keys = rng.sample(ASPECT_ORDER, n)
    pols = [rng.choices(["pos", "neg", "neu"], prof.get(k, DEFAULT))[0] for k in keys]
    text = rng.choice(ASPECTS[keys[0]][pols[0]])
    for i in range(1, n):
        link = CONTRAST if pols[i] != pols[i - 1] else SAME
        text += rng.choice(link) + rng.choice(ASPECTS[keys[i]][pols[i]])
    has_pos, has_neg = "pos" in pols, "neg" in pols
    label = "pos" if (has_pos and not has_neg) else "neg" if (has_neg and not has_pos) else "neu"
    if rng.random() < 0.5:
        text += " " + rng.choice(ENDS[label])
    text += rng.choice(SUFFIX)
    rating = {"pos": rng.choice([4, 5]), "neu": 3, "neg": rng.choice([1, 2])}[label]
    return text, label, sorted(keys, key=ASPECT_ORDER.index), rating


def main():
    rng = random.Random(SEED)
    rows = []
    for gid in PROFILES:
        seen = set()
        while len([r for r in rows if r["gym_id"] == gid]) < PER_GYM:
            text, label, aspects, rating = build(rng, gid)
            if text in seen:
                continue
            seen.add(text)
            when = END - dt.timedelta(days=rng.random() * DAYS)
            when = when.replace(hour=rng.choice([7, 8, 12, 17, 18, 19, 20]),
                                minute=rng.randrange(60), second=0, microsecond=0)
            rows.append({"gym_id": gid, "rating": rating, "text": text, "sentiment": label,
                         "aspects": ";".join(aspects), "created_at": when.isoformat()})
    df = pd.DataFrame(rows).sort_values("created_at").reset_index(drop=True)
    Path("data").mkdir(exist_ok=True)
    df.to_csv("data/reviews_gym.csv", index=False, encoding="utf-8-sig")
    print(f"สร้างรีวิว {len(df)} รายการ")
    print(df.groupby("gym_id").agg(n=("rating", "size"), avg=("rating", "mean")).round(2).to_string())


if __name__ == "__main__":
    main()
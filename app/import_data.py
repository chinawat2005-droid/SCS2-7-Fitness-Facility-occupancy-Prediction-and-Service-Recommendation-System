import pandas as pd
from app.database import engine

gyms = pd.read_csv("data/gyms.csv")
occupancy = pd.read_csv("data/occupancy.csv")

gyms.to_sql("gyms", engine, if_exists="replace", index=False)
occupancy.to_sql("occupancy", engine, if_exists="replace", index=False)
print(f"gyms={len(gyms)} occupancy={len(occupancy)}")

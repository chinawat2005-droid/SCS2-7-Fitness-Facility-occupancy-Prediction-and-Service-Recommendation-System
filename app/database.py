from sqlalchemy import create_engine

engine = create_engine(
    "sqlite:///gym.db", connect_args={"check_same_thread": False}
)

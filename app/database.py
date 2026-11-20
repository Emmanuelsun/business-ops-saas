import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL is missing. Check your .env file.")


def normalize_database_url(url: str) -> str:
    # Hosting services give plain "postgres://" or "postgresql://" addresses.
    # This project uses the psycopg2 driver, so name it explicitly.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


# pool_pre_ping checks a connection before using it, so a database that went
# to sleep (as free hosted databases do) is reconnected instead of failing.
engine = create_engine(normalize_database_url(DATABASE_URL), pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# End of file.
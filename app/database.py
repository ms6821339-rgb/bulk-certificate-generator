from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

# SQLite needs this flag because FastAPI may use the connection from
# different threads; other databases don't need it.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {} #SQLite needs this as it only works throug one thread, this tells it to work for more than one thread. Other databases don't need this flag.

engine = create_engine(DATABASE_URL, connect_args=connect_args) #crates an entry point for the database, this is the engine that will be used to connect to the database.

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False) #represents one database session, this is used to interact with the database. It can be thouht of as a trip to the database(function call)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
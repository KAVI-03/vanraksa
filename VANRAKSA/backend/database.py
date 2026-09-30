"""
Database — Synchronous SQLAlchemy with SQLite
Using sync engine (no aiosqlite/greenlet) for Python 3.14 compatibility.
FastAPI endpoints use run_in_executor pattern for non-blocking I/O.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from config import settings
import threading

# Strip aiosqlite prefix if present — use plain sqlite for sync engine
db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")

engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False},
    echo=(settings.APP_ENV == "development"),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a synchronous DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Call on startup."""
    from models import user, trip, incident, geofence, ranger, network_coverage, advisory  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _migrate_users_full_name()
    _migrate_users_last_login()
    _migrate_users_location()
    _migrate_identity_document()


def _migrate_users_full_name():
    """Add users.full_name to databases created before registration captured a name."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("users")]
    if "full_name" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR"))


def _migrate_users_last_login():
    """Add users.last_login_at to databases created before it existed."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("users")]
    if "last_login_at" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN last_login_at DATETIME"))


def _migrate_users_location():
    """Add the latest tourist GPS fields to existing user tables."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    columns = {column["name"] for column in insp.get_columns("users")}
    additions = {
        "last_lat": "FLOAT",
        "last_lng": "FLOAT",
        "location_accuracy_m": "FLOAT",
        "location_speed_kmh": "FLOAT",
        "location_updated_at": "DATETIME",
    }
    with engine.begin() as connection:
        for name, column_type in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {column_type}"))


def _migrate_identity_document():
    """Add identity_records.document_path to databases created before uploads existed."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    if "identity_records" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("identity_records")]
    if "document_path" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE identity_records ADD COLUMN document_path VARCHAR"))

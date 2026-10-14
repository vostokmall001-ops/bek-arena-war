import json
from datetime import datetime

from sqlalchemy import DateTime, text

from backend.database import SessionLocal, engine
from backend.models import Building, BaseCamp, User

BACKUP_VERSION = 1

# Tartib muhim: avval users, keyin bases, oxirida buildings (FK bog'lanishi)
TABLES = [("users", User), ("bases", BaseCamp), ("buildings", Building)]


def _serialize(value):
    return value.isoformat() if isinstance(value, datetime) else value


def export_data() -> bytes:
    """Barcha jadvallarni JSON fayl (bytes) ko'rinishida qaytaradi."""
    db = SessionLocal()
    try:
        data = {
            "version": BACKUP_VERSION,
            "created_at": datetime.utcnow().isoformat(),
            "tables": {},
        }
        for name, model in TABLES:
            rows = []
            for obj in db.query(model).order_by(model.id).all():
                rows.append({c.name: _serialize(getattr(obj, c.name)) for c in model.__table__.columns})
            data["tables"][name] = rows
        return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    finally:
        db.close()


def _deserialize_row(model, row: dict) -> dict:
    out = {}
    for col in model.__table__.columns:
        if col.name not in row:
            continue
        value = row[col.name]
        if value is not None and isinstance(col.type, DateTime):
            value = datetime.fromisoformat(value)
        out[col.name] = value
    return out


def import_data(raw: bytes) -> dict:
    """JSON backupdan bazani to'liq tiklaydi (mavjud ma'lumot o'chiriladi).
    Xato bo'lsa hech narsa o'zgarmaydi (bitta tranzaksiya)."""
    data = json.loads(raw.decode("utf-8"))

    if not isinstance(data, dict) or data.get("version") != BACKUP_VERSION or "tables" not in data:
        raise ValueError("Bu BEK ARENA backup fayli emas yoki versiyasi mos emas")

    tables = data["tables"]
    for name, _ in TABLES:
        if not isinstance(tables.get(name), list):
            raise ValueError(f"Faylda '{name}' jadvali topilmadi")

    db = SessionLocal()
    try:
        for _, model in reversed(TABLES):
            db.query(model).delete()

        for name, model in TABLES:
            for row in tables[name]:
                db.add(model(**_deserialize_row(model, row)))
            db.flush()

        # Postgresda ID'lar qo'lda kiritilgani uchun sequence'ni to'g'rilash kerak
        if engine.dialect.name == "postgresql":
            for name, _ in TABLES:
                db.execute(
                    text(
                        f"SELECT setval(pg_get_serial_sequence('{name}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {name}), 1), "
                        f"(SELECT MAX(id) FROM {name}) IS NOT NULL)"
                    )
                )

        db.commit()
        return {name: len(tables[name]) for name, _ in TABLES}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

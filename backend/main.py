import hashlib
import hmac
import json
import time
from datetime import datetime
from urllib.parse import parse_qsl

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import Base, engine, get_db
from backend.models import Building, BaseCamp, User

Base.metadata.create_all(bind=engine)

app = FastAPI(title="BEK ARENA: WAR API", version="1.0.0")

# Autentifikatsiya header orqali bo'lgani uchun cookie/credentials kerak emas.
# (allow_origins=["*"] bilan allow_credentials=True birga ishlamaydi.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEV_USER = {"id": 123456789, "username": "test_commander"}


def verify_telegram_init_data(init_data: str) -> dict:
    # Faqat development rejimida test uchun
    if settings.ENVIRONMENT == "development" and init_data == "test_token":
        return DEV_USER

    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid init data format")

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=403, detail="Missing hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    # Telegram WebApp qoidasi: secret = HMAC_SHA256(key="WebAppData", msg=BOT_TOKEN)
    secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(status_code=403, detail="Telegram auth signature mismatch!")

    # Eski (replay) so'rovlarni rad etish
    try:
        auth_date = int(parsed.get("auth_date", "0"))
    except ValueError:
        auth_date = 0
    if time.time() - auth_date > settings.INIT_DATA_MAX_AGE:
        raise HTTPException(status_code=403, detail="Init data expired")

    try:
        user_info = json.loads(parsed.get("user", "{}"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=403, detail="Invalid user data")

    if not isinstance(user_info, dict) or "id" not in user_info:
        raise HTTPException(status_code=403, detail="User id missing")
    return user_info


def create_user_with_base(db: Session, telegram_id: int, username: str) -> User:
    user = User(telegram_id=telegram_id, username=username)
    db.add(user)
    db.flush()  # user.id olish uchun

    base = BaseCamp(user_id=user.id, gold=1000.0, oil=500.0)
    db.add(base)
    db.flush()

    db.add(Building(base_id=base.id, building_type="hq", level=1, position_x=2, position_y=2))
    db.add(Building(base_id=base.id, building_type="gold_mine", level=1, position_x=0, position_y=0))
    db.add(Building(base_id=base.id, building_type="oil_pump", level=1, position_x=4, position_y=0))
    db.commit()  # hammasi bitta tranzaksiyada
    db.refresh(user)
    return user


@app.post("/api/auth")
def authenticate_user(x_telegram_init_data: str = Header(...), db: Session = Depends(get_db)):
    tg_user = verify_telegram_init_data(x_telegram_init_data)
    telegram_id = tg_user["id"]
    username = tg_user.get("username") or "Commander"

    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        try:
            user = create_user_with_base(db, telegram_id, username)
        except IntegrityError:
            # Ikki parallel so'rov bir vaqtda user yaratmoqchi bo'lsa
            db.rollback()
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                raise HTTPException(status_code=500, detail="Could not create user")

    base = db.query(BaseCamp).filter(BaseCamp.user_id == user.id).first()
    if not base:
        raise HTTPException(status_code=404, detail="Base not found")

    # Vaqt o'tishi bilan passiv resurs yig'ilishi
    now = datetime.utcnow()
    seconds_passed = (now - base.last_update).total_seconds()
    if seconds_passed > 0:
        gold_income = (base.hq_level * 2.5) * (seconds_passed / 60.0)
        oil_income = (base.hq_level * 1.5) * (seconds_passed / 60.0)

        base.gold = min(base.gold_capacity, base.gold + gold_income)
        base.oil = min(base.oil_capacity, base.oil + oil_income)
        base.last_update = now
        db.commit()

    buildings = db.query(Building).filter(Building.base_id == base.id).all()

    return {
        "status": "success",
        "user": {"id": user.id, "username": user.username},
        "base": {
            "hq_level": base.hq_level,
            "gold": round(base.gold, 1),
            "oil": round(base.oil, 1),
            "gold_capacity": base.gold_capacity,
            "oil_capacity": base.oil_capacity,
        },
        "buildings": [
            {"id": b.id, "type": b.building_type, "level": b.level, "x": b.position_x, "y": b.position_y}
            for b in buildings
        ],
    }


@app.post("/api/attack/bot")
def attack_bot(x_telegram_init_data: str = Header(...), db: Session = Depends(get_db)):
    tg_user = verify_telegram_init_data(x_telegram_init_data)
    user = db.query(User).filter(User.telegram_id == tg_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    base = db.query(BaseCamp).filter(BaseCamp.user_id == user.id).first()
    if not base:
        raise HTTPException(status_code=404, detail="Base not found")

    reward_gold = 350.0
    reward_oil = 180.0

    base.gold = min(base.gold_capacity, base.gold + reward_gold)
    base.oil = min(base.oil_capacity, base.oil + reward_oil)
    db.commit()

    return {
        "status": "victory",
        "reward_gold": reward_gold,
        "reward_oil": reward_oil,
        "new_gold": round(base.gold, 1),
        "new_oil": round(base.oil, 1),
    }

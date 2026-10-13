from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import hmac
import hashlib
urllib = __import__("urllib.parse", fromlist=["parse_qsl"])

from backend.database import engine, Base, get_db
from backend.models import User, BaseCamp, Building
from backend.config import settings

Base.metadata.create_all(bind=engine)

app = FastAPI(title="BEK ARENA: WAR API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_telegram_init_data(init_data: str) -> dict:
    if settings.ENVIRONMENT == "development" and init_data == "test_token":
        return {"id": 123456789, "username": "test_commander"}
    
    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data))
        hash_val = parsed_data.pop('hash', '')
        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(parsed_data.items())])
        
        secret_key = hashlib.sha256(settings.BOT_TOKEN.encode()).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash != hash_val:
            raise HTTPException(status_code=403, detail="Telegram auth signature mismatch!")
        
        import json
        user_info = json.loads(parsed_data.get('user', '{}'))
        return user_info
    except Exception as e:
        if settings.ENVIRONMENT == "development":
            return {"id": 123456789, "username": "test_commander"}
        raise HTTPException(status_code=403, detail=f"Authentication failed: {str(e)}")

@app.post("/api/auth")
def authenticate_user(x_telegram_init_data: str = Header(...), db: Session = Depends(get_db)):
    tg_user = verify_telegram_init_data(x_telegram_init_data)
    telegram_id = tg_user.get("id")
    username = tg_user.get("username", "Commander")

    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, username=username)
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create base camp
        base = BaseCamp(user_id=user.id, gold=1000.0, oil=500.0)
        db.add(base)
        db.commit()
        db.refresh(base)

        # Add starter buildings
        db.add(Building(base_id=base.id, building_type="hq", level=1, position_x=2, position_y=2))
        db.add(Building(base_id=base.id, building_type="gold_mine", level=1, position_x=0, position_y=0))
        db.add(Building(base_id=base.id, building_type="oil_pump", level=1, position_x=4, position_y=0))
        db.commit()

    base = db.query(BaseCamp).filter(BaseCamp.user_id == user.id).first()
    
    # Calculate passive resource generation based on time passed
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
            "oil_capacity": base.oil_capacity
        },
        "buildings": [{"id": b.id, "type": b.building_type, "level": b.level, "x": b.position_x, "y": b.position_y} for b in buildings]
    }

@app.post("/api/attack/bot")
def attack_bot(x_telegram_init_data: str = Header(...), db: Session = Depends(get_db)):
    tg_user = verify_telegram_init_data(x_telegram_init_data)
    user = db.query(User).filter(User.telegram_id == tg_user.get("id")).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    base = db.query(BaseCamp).filter(BaseCamp.user_id == user.id).first()
    
    # Simulate battle logic on backend server securely
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
        "new_oil": round(base.oil, 1)
    }

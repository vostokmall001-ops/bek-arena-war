from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, String

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # Telegram ID 32-bitdan katta bo'lishi mumkin -> BigInteger
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BaseCamp(Base):
    __tablename__ = "bases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    hq_level = Column(Integer, default=1)
    gold = Column(Float, default=1000.0)
    oil = Column(Float, default=500.0)
    gold_capacity = Column(Float, default=5000.0)
    oil_capacity = Column(Float, default=2500.0)
    last_update = Column(DateTime, default=datetime.utcnow)


class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    base_id = Column(Integer, ForeignKey("bases.id"), nullable=False)
    building_type = Column(String, nullable=False)  # hq, gold_mine, oil_pump, barracks, defense_tower
    level = Column(Integer, default=1)
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)

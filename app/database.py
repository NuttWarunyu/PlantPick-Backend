from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, ForeignKey, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:NXNHZKLEvwCdsDHQqzrFsREUgaFNYLPC@${RAILWAY_PRIVATE_DOMAIN}:5432/railway")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define Models (เหมือนเดิม)
class UsageLimit(Base):
    __tablename__ = "usage_limits"
    limit_id = Column(Integer, primary_key=True)
    user_ip = Column(String)
    daily_limit = Column(Integer)
    daily_used = Column(Integer)
    last_reset = Column(TIMESTAMP)

class GenerationHistory(Base):
    __tablename__ = "generation_history"
    history_id = Column(Integer, primary_key=True)
    ip = Column(String)
    image_url = Column(String)
    prompt = Column(Text)
    created_at = Column(TIMESTAMP)
    ddim_steps = Column(Integer)
    user_agent = Column(String)

class BOMDetail(Base):
    __tablename__ = "bom_details"
    bom_id = Column(Integer, primary_key=True)
    history_id = Column(Integer, ForeignKey("generation_history.history_id"))
    material_name = Column(String)
    quantity = Column(Integer)
    estimated_cost = Column(DECIMAL)
    affiliate_link = Column(String)
    created_at = Column(TIMESTAMP)

class GardenRequest(Base):
    __tablename__ = "garden_requests"
    request_id = Column(Integer, primary_key=True)
    history_id = Column(Integer, ForeignKey("generation_history.history_id"))
    budget = Column(DECIMAL)
    location = Column(String)
    additional_details = Column(Text)
    status = Column(String)
    created_at = Column(TIMESTAMP)
    fee_charged = Column(DECIMAL)

# สร้างตาราง
Base.metadata.create_all(bind=engine)
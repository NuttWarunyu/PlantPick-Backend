from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, ForeignKey, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# ตรวจสอบและกำหนด DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback to local PostgreSQL if no DATABASE_URL is set
    DATABASE_URL = os.getenv("LOCAL_DATABASE_URL", "postgresql://postgres:password@localhost:5432/plantpick")
    print(f"Warning: DATABASE_URL not found, falling back to {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL)
    # ตรวจสอบการเชื่อมต่อ (ถ้า fail จะ raise exception)
    with engine.connect() as connection:
        connection.close()
    print("Database connection established successfully")
except Exception as e:
    raise ConnectionError(f"Failed to connect to database: {str(e)}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define Models
class UsageLimit(Base):
    __tablename__ = "usage_limits"
    limit_id = Column(Integer, primary_key=True)
    user_ip = Column(String, nullable=False)
    daily_limit = Column(Integer, default=3)
    daily_used = Column(Integer, default=0)
    last_reset = Column(TIMESTAMP)

class GenerationHistory(Base):
    __tablename__ = "generation_history"
    history_id = Column(Integer, primary_key=True)
    ip = Column(String, nullable=False)
    image_url = Column(String)
    prompt = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)
    ddim_steps = Column(Integer, default=10)
    user_agent = Column(String)

class BOMDetail(Base):
    __tablename__ = "bom_details"
    bom_id = Column(Integer, primary_key=True)
    history_id = Column(Integer, ForeignKey("generation_history.history_id"), nullable=False)
    material_name = Column(String, nullable=False)     # เช่น "ต้นไม้"
    quantity = Column(DECIMAL(10, 2), nullable=False)  # เช่น 5.00
    estimated_cost = Column(DECIMAL(10, 2), nullable=False)  # บาท
    affiliate_link = Column(String)
    created_at = Column(TIMESTAMP, nullable=False)

class GardenRequest(Base):
    __tablename__ = "garden_requests"
    request_id = Column(Integer, primary_key=True)
    history_id = Column(Integer, ForeignKey("generation_history.history_id"), nullable=False)
    budget = Column(DECIMAL(10, 2), nullable=False)
    location = Column(String, nullable=False)
    additional_details = Column(Text)
    status = Column(String, default="pending")
    created_at = Column(TIMESTAMP, nullable=False)
    fee_charged = Column(DECIMAL(10, 2), default=0.00)
    total_cost = Column(DECIMAL(10, 2), nullable=True)

# สร้างตาราง (เพิ่มเงื่อนไขไม่สร้างซ้ำ)
def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized or already exist.")

if __name__ == "__main__":
    init_db()
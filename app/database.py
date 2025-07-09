from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, ForeignKey, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# โหลด .env ก่อนทำอย่างอื่น
load_dotenv()

# ตรวจสอบสภาพแวดล้อม (Environment)
IS_PRODUCTION = os.getenv("RAILWAY_ENVIRONMENT") is not None

if IS_PRODUCTION:
    # เมื่อรันบน Railway ให้ใช้ DATABASE_URL (ที่อยู่ภายใน)
    DATABASE_URL = os.getenv("DATABASE_URL")
    print("✅ Running in PRODUCTION mode. Using internal database URL.")
else:
    # เมื่อรันบนเครื่อง (Local) ให้ใช้ LOCAL_DATABASE_URL ที่คุณตั้งไว้
    DATABASE_URL = os.getenv("LOCAL_DATABASE_URL")
    print("✅ Running in LOCAL mode. Using local database URL.")

# ตรวจสอบว่ามี URL หรือไม่
if not DATABASE_URL:
    raise ConnectionError(
        "Database URL is not set. Please check your .env file and ensure "
        "either DATABASE_URL (for production) or LOCAL_DATABASE_URL (for local) is set."
    )

try:
    engine = create_engine(DATABASE_URL)
    # ตรวจสอบการเชื่อมต่อ
    with engine.connect() as connection:
        connection.close()
    print("🚀 Database connection established successfully!")
except Exception as e:
    # แสดง Error ที่ชัดเจนขึ้น
    print(f"❌ Failed to connect to database using URL: {DATABASE_URL}")
    raise ConnectionError(f"Failed to connect to database: {str(e)}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# โค้ดส่วน Model ที่ถูกต้องทั้งหมดจะอยู่ตรงนี้
class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True)
    created_at = Column(TIMESTAMP, server_default='now()')
    material_name = Column(String, nullable=False) # ชื่อภาษาไทยสำหรับแสดงผล
    name_en = Column(String, nullable=True) # ชื่อภาษาอังกฤษ
    style_tag = Column(String)
    unit_price_thb = Column(DECIMAL(10, 2), nullable=False, default=0)
    unit_type = Column(String, nullable=False)
    affiliate_link = Column(String)

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
    material_name = Column(String, nullable=False)
    quantity = Column(DECIMAL(10, 2), nullable=False)
    estimated_cost = Column(DECIMAL(10, 2), nullable=False)
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

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized or already exist.")

if __name__ == "__main__":
    init_db()

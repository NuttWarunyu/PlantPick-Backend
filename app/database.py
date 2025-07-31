from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, ForeignKey, DECIMAL, Boolean, Numeric
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import time
from dotenv import load_dotenv

load_dotenv()

IS_PRODUCTION = os.getenv("RAILWAY_ENVIRONMENT") is not None

if IS_PRODUCTION:
    DATABASE_URL = os.getenv("DATABASE_URL")
    print("✅ Running in PRODUCTION mode. Using internal database URL.")
else:
    # Use default SQLite for local development if no database URL is set
    DATABASE_URL = os.getenv("LOCAL_DATABASE_URL", "sqlite:///./plantpick_local.db")
    print("✅ Running in LOCAL mode. Using local database URL.")

if not DATABASE_URL:
    raise ConnectionError("Database URL is not set.")

MAX_RETRIES = 5
RETRY_DELAY = 5

for attempt in range(MAX_RETRIES):
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            connection.close()
        print(f"🚀 Database connection established successfully on attempt {attempt + 1}!")
        break
    except Exception as e:
        print(f"⚠️ Attempt {attempt + 1}/{MAX_RETRIES}: Failed to connect to database. Retrying in {RETRY_DELAY} seconds...")
        print(f"   Error: {e}")
        if attempt + 1 == MAX_RETRIES:
            print("❌ All attempts to connect to the database have failed.")
            print("💡 Using SQLite for local development...")
            # Fallback to SQLite for local development
            DATABASE_URL = "sqlite:///./plantpick_local.db"
            engine = create_engine(DATABASE_URL)
            break
        time.sleep(RETRY_DELAY)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# (โมเดลอื่นๆ เหมือนเดิม)
class Material(Base):
    __tablename__ = "materials"; id = Column(Integer, primary_key=True); material_name = Column(String(255), nullable=False); name_en = Column(String(255)); category = Column(String(100)); style_tag = Column(String(100)); description = Column(Text); created_at = Column(TIMESTAMP(timezone=True), server_default='now()')
class Vendor(Base):
    __tablename__ = "vendors"; id = Column(Integer, primary_key=True); vendor_name = Column(String(255), nullable=False); location = Column(Text); rating = Column(Numeric(2, 1), default=0.0); has_installation_service = Column(Boolean, default=False); created_at = Column(TIMESTAMP(timezone=True), server_default='now()')
class Product(Base):
    __tablename__ = "products"; id = Column(Integer, primary_key=True); material_id = Column(Integer, ForeignKey("materials.id"), nullable=False); vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False); price_thb = Column(DECIMAL(10, 2), nullable=False); unit_type = Column(String(50), nullable=False); product_url = Column(Text); created_at = Column(TIMESTAMP(timezone=True), server_default='now()')
class AITermMapping(Base):
    __tablename__ = "ai_term_mappings"; id = Column(Integer, primary_key=True); ai_term = Column(String(255), nullable=False, unique=True); maps_to_category = Column(String(100))

# === จุดแก้ไข: เพิ่มคอลัมน์ user_agent กลับเข้ามาในโมเดล ===
class GenerationHistory(Base):
    __tablename__ = "generation_history"
    history_id = Column(Integer, primary_key=True)
    replicate_prediction_id = Column(String(255), nullable=True, index=True)
    ip = Column(String, nullable=False)
    image_url = Column(String)
    prompt = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)
    selected_tags = Column(ARRAY(Text))
    budget_level = Column(Integer)
    user_agent = Column(String) # <-- เพิ่มคอลัมน์นี้กลับเข้ามา

class BOMDetail(Base):
    __tablename__ = "bom_details"; bom_id = Column(Integer, primary_key=True); history_id = Column(Integer, ForeignKey("generation_history.history_id"), nullable=False); material_name = Column(String, nullable=False); quantity = Column(DECIMAL(10, 2), nullable=False); estimated_cost = Column(DECIMAL(10, 2), nullable=False); affiliate_link = Column(String); created_at = Column(TIMESTAMP, nullable=False)
class GardenRequest(Base):
    __tablename__ = "garden_requests"; request_id = Column(Integer, primary_key=True); history_id = Column(Integer, ForeignKey("generation_history.history_id"), nullable=False); budget = Column(DECIMAL(10, 2), nullable=False); location = Column(String, nullable=False); additional_details = Column(Text); status = Column(String, default="pending"); created_at = Column(TIMESTAMP, nullable=False); total_cost = Column(DECIMAL(10, 2), nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables checked/created.")

if __name__ == "__main__":
    init_db()

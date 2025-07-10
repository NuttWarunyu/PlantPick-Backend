from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, ForeignKey, DECIMAL, Boolean, Numeric
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

IS_PRODUCTION = os.getenv("RAILWAY_ENVIRONMENT") is not None

if IS_PRODUCTION:
    DATABASE_URL = os.getenv("DATABASE_URL")
    print("✅ Running in PRODUCTION mode. Using internal database URL.")
else:
    DATABASE_URL = os.getenv("LOCAL_DATABASE_URL")
    print("✅ Running in LOCAL mode. Using local/public database URL.")

if not DATABASE_URL:
    raise ConnectionError("Database URL is not set.")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        connection.close()
    print("🚀 Database connection established successfully!")
except Exception as e:
    print(f"❌ Failed to connect to database using URL: {DATABASE_URL}")
    raise ConnectionError(f"Failed to connect to database: {str(e)}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# (โมเดล Material, Vendor, Product, material_relationships เหมือนเดิม)
# ... (โค้ดส่วนนี้ไม่มีการเปลี่ยนแปลง)
class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True)
    material_name = Column(String(255), nullable=False)
    name_en = Column(String(255))
    category = Column(String(100))
    description = Column(Text)
    image_url = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default='now()')
    sun_requirement = Column(String(50))
    water_requirement = Column(String(50))
    is_native_th = Column(Boolean)
    soil_type = Column(Text)

class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(Integer, primary_key=True)
    vendor_name = Column(String(255), nullable=False)
    contact_person = Column(String(255))
    phone_number = Column(String(20))
    line_id = Column(String(100))
    location = Column(Text)
    rating = Column(Numeric(2, 1), default=0.0)
    created_at = Column(TIMESTAMP(timezone=True), server_default='now()')
    delivery_areas = Column(ARRAY(Text))
    has_installation_service = Column(Boolean, default=False)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    price_thb = Column(DECIMAL(10, 2), nullable=False)
    unit_type = Column(String(50), nullable=False)
    stock_quantity = Column(Integer, default=0)
    product_url = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default='now()')
    size_options = Column(JSONB)

class material_relationships(Base):
    __tablename__ = "material_relationships"
    material_id_1 = Column(Integer, ForeignKey("materials.id"), primary_key=True)
    material_id_2 = Column(Integer, ForeignKey("materials.id"), primary_key=True)
    relationship_type = Column(String(100))
    notes = Column(Text)
# ... (จบส่วนที่ไม่มีการเปลี่ยนแปลง)


# === จุดแก้ไข: เพิ่มคอลัมน์ replicate_prediction_id ===
class GenerationHistory(Base):
    __tablename__ = "generation_history"
    history_id = Column(Integer, primary_key=True)
    replicate_prediction_id = Column(String(255), nullable=True, index=True) # <-- เพิ่มคอลัมน์นี้
    ip = Column(String, nullable=False)
    image_url = Column(String)
    prompt = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)
    ddim_steps = Column(Integer, default=10)
    user_agent = Column(String)
    selected_tags = Column(ARRAY(Text))
    budget_level = Column(Integer)

# (โมเดล BOMDetail, GardenRequest เหมือนเดิม)
# ... (โค้ดส่วนนี้ไม่มีการเปลี่ยนแปลง)
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
# ... (จบส่วนที่ไม่มีการเปลี่ยนแปลง)


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables checked/created.")

if __name__ == "__main__":
    init_db()

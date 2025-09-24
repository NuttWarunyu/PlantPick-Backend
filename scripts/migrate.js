const { Pool } = require('pg');

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

async function migrate() {
  try {
    console.log('Starting database migration...');

    // Create plants table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS plants (
        id VARCHAR(50) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        scientific_name VARCHAR(255),
        category VARCHAR(100),
        plant_type VARCHAR(100),
        measurement_type VARCHAR(100),
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
      )
    `);

    // Create suppliers table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS suppliers (
        id VARCHAR(50) PRIMARY KEY,
        plant_id VARCHAR(50) REFERENCES plants(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        phone VARCHAR(20),
        location VARCHAR(255),
        size VARCHAR(100),
        last_updated TIMESTAMP DEFAULT NOW(),
        created_at TIMESTAMP DEFAULT NOW()
      )
    `);

    // Insert sample data
    await pool.query(`
      INSERT INTO plants (id, name, scientific_name, category, plant_type, measurement_type)
      VALUES 
        ('plant_001', 'ต้นยางอินเดีย', 'Ficus elastica', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_002', 'ต้นมอนสเตอร่า', 'Monstera deliciosa', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_003', 'ต้นฟิโลเดนดรอน', 'Philodendron', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_004', 'ต้นยางใบ', 'Ficus lyrata', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_005', 'ต้นไผ่กวนอิม', 'Dracaena sanderiana', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_006', 'ต้นเศรษฐีเรือนใน', 'Chlorophytum comosum', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_007', 'ต้นคล้า', 'Calathea', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_008', 'ต้นเศรษฐีเรือนนอก', 'Chlorophytum comosum', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_009', 'ต้นไทร', 'Ficus benjamina', 'ไม้ล้อม', 'ไม้ล้อม', 'ความสูง'),
        ('plant_010', 'ต้นจามจุรี', 'Samanea saman', 'ไม้ล้อม', 'ไม้ล้อม', 'ความสูง')
      ON CONFLICT (id) DO NOTHING
    `);

    // Insert sample suppliers
    await pool.query(`
      INSERT INTO suppliers (id, plant_id, name, price, phone, location, size)
      VALUES 
        ('supplier_001', 'plant_001', 'สวนไม้ประดับไทย', 150, '081-234-5678', 'กรุงเทพฯ', '30-40 ซม.'),
        ('supplier_002', 'plant_002', 'ร้านต้นไม้สวยงาม', 200, '082-345-6789', 'เชียงใหม่', '40-50 ซม.'),
        ('supplier_003', 'plant_003', 'สวนไม้ประดับไทย', 180, '081-234-5678', 'กรุงเทพฯ', '35-45 ซม.'),
        ('supplier_004', 'plant_004', 'ร้านต้นไม้สวยงาม', 250, '082-345-6789', 'เชียงใหม่', '45-55 ซม.'),
        ('supplier_005', 'plant_005', 'สวนไม้ประดับไทย', 120, '081-234-5678', 'กรุงเทพฯ', '25-35 ซม.'),
        ('supplier_006', 'plant_006', 'ร้านต้นไม้สวยงาม', 100, '082-345-6789', 'เชียงใหม่', '20-30 ซม.'),
        ('supplier_007', 'plant_007', 'สวนไม้ประดับไทย', 160, '081-234-5678', 'กรุงเทพฯ', '30-40 ซม.'),
        ('supplier_008', 'plant_008', 'ร้านต้นไม้สวยงาม', 90, '082-345-6789', 'เชียงใหม่', '15-25 ซม.'),
        ('supplier_009', 'plant_009', 'สวนไม้ประดับไทย', 300, '081-234-5678', 'กรุงเทพฯ', '50-60 ซม.'),
        ('supplier_010', 'plant_010', 'ร้านต้นไม้สวยงาม', 400, '082-345-6789', 'เชียงใหม่', '60-70 ซม.')
      ON CONFLICT (id) DO NOTHING
    `);

    console.log('Database migration completed successfully!');
    console.log('Created tables: plants, suppliers');
    console.log('Inserted sample data: 10 plants, 10 suppliers');

  } catch (error) {
    console.error('Migration failed:', error);
    throw error;
  } finally {
    await pool.end();
  }
}

// Run migration if called directly
if (require.main === module) {
  migrate().catch(console.error);
}

module.exports = { migrate };

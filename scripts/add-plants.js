const { Pool } = require('pg');

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

async function addPlants() {
  try {
    console.log('Adding more plants data...');

    // Insert more plants
    await pool.query(`
      INSERT INTO plants (id, name, scientific_name, category, plant_type, measurement_type)
      VALUES 
        -- ไม้ประดับ
        ('plant_011', 'ต้นเศรษฐีเรือนใน', 'Chlorophytum comosum', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_012', 'ต้นเศรษฐีเรือนนอก', 'Chlorophytum comosum', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_013', 'ต้นคล้า', 'Calathea', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_014', 'ต้นไผ่กวนอิม', 'Dracaena sanderiana', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_015', 'ต้นยางอินเดีย', 'Ficus elastica', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_016', 'ต้นมอนสเตอร่า', 'Monstera deliciosa', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_017', 'ต้นฟิโลเดนดรอน', 'Philodendron', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_018', 'ต้นยางใบ', 'Ficus lyrata', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_019', 'ต้นไทร', 'Ficus benjamina', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        ('plant_020', 'ต้นจามจุรี', 'Samanea saman', 'ไม้ประดับ', 'ไม้ประดับ', 'ความสูง'),
        
        -- ไม้ล้อม
        ('plant_021', 'ต้นประดู่', 'Pterocarpus indicus', 'ไม้ล้อม', 'ไม้ล้อม', 'ความสูง'),
        ('plant_022', 'ต้นมะขาม', 'Tamarindus indica', 'ไม้ล้อม', 'ไม้ล้อม', 'ความสูง'),
        ('plant_023', 'ต้นจามจุรี', 'Samanea saman', 'ไม้ล้อม', 'ไม้ล้อม', 'ความสูง'),
        ('plant_024', 'ต้นไทร', 'Ficus benjamina', 'ไม้ล้อม', 'ไม้ล้อม', 'ความสูง'),
        ('plant_025', 'ต้นประดู่', 'Pterocarpus indicus', 'ไม้ล้อม', 'ไม้ล้อม', 'ความสูง'),
        
        -- ไม้คลุมดิน
        ('plant_026', 'ต้นคล้า', 'Calathea', 'ไม้คลุมดิน', 'ไม้คลุมดิน', 'ความสูง'),
        ('plant_027', 'ต้นเศรษฐีเรือนใน', 'Chlorophytum comosum', 'ไม้คลุมดิน', 'ไม้คลุมดิน', 'ความสูง'),
        ('plant_028', 'ต้นเศรษฐีเรือนนอก', 'Chlorophytum comosum', 'ไม้คลุมดิน', 'ไม้คลุมดิน', 'ความสูง'),
        ('plant_029', 'ต้นไผ่กวนอิม', 'Dracaena sanderiana', 'ไม้คลุมดิน', 'ไม้คลุมดิน', 'ความสูง'),
        ('plant_030', 'ต้นคล้า', 'Calathea', 'ไม้คลุมดิน', 'ไม้คลุมดิน', 'ความสูง')
      ON CONFLICT (id) DO NOTHING
    `);

    // Insert more suppliers
    await pool.query(`
      INSERT INTO suppliers (id, plant_id, name, price, phone, location, size)
      VALUES 
        -- ไม้ประดับ
        ('supplier_011', 'plant_011', 'สวนไม้ประดับไทย', 100, '081-234-5678', 'กรุงเทพฯ', '20-30 ซม.'),
        ('supplier_012', 'plant_012', 'ร้านต้นไม้สวยงาม', 90, '082-345-6789', 'เชียงใหม่', '15-25 ซม.'),
        ('supplier_013', 'plant_013', 'สวนไม้ประดับไทย', 160, '081-234-5678', 'กรุงเทพฯ', '30-40 ซม.'),
        ('supplier_014', 'plant_014', 'ร้านต้นไม้สวยงาม', 120, '082-345-6789', 'เชียงใหม่', '25-35 ซม.'),
        ('supplier_015', 'plant_015', 'สวนไม้ประดับไทย', 150, '081-234-5678', 'กรุงเทพฯ', '30-40 ซม.'),
        ('supplier_016', 'plant_016', 'ร้านต้นไม้สวยงาม', 200, '082-345-6789', 'เชียงใหม่', '40-50 ซม.'),
        ('supplier_017', 'plant_017', 'สวนไม้ประดับไทย', 180, '081-234-5678', 'กรุงเทพฯ', '35-45 ซม.'),
        ('supplier_018', 'plant_018', 'ร้านต้นไม้สวยงาม', 250, '082-345-6789', 'เชียงใหม่', '45-55 ซม.'),
        ('supplier_019', 'plant_019', 'สวนไม้ประดับไทย', 300, '081-234-5678', 'กรุงเทพฯ', '50-60 ซม.'),
        ('supplier_020', 'plant_020', 'ร้านต้นไม้สวยงาม', 400, '082-345-6789', 'เชียงใหม่', '60-70 ซม.'),
        
        -- ไม้ล้อม
        ('supplier_021', 'plant_021', 'สวนไม้ประดับไทย', 500, '081-234-5678', 'กรุงเทพฯ', '70-80 ซม.'),
        ('supplier_022', 'plant_022', 'ร้านต้นไม้สวยงาม', 600, '082-345-6789', 'เชียงใหม่', '80-90 ซม.'),
        ('supplier_023', 'plant_023', 'สวนไม้ประดับไทย', 400, '081-234-5678', 'กรุงเทพฯ', '60-70 ซม.'),
        ('supplier_024', 'plant_024', 'ร้านต้นไม้สวยงาม', 300, '082-345-6789', 'เชียงใหม่', '50-60 ซม.'),
        ('supplier_025', 'plant_025', 'สวนไม้ประดับไทย', 500, '081-234-5678', 'กรุงเทพฯ', '70-80 ซม.'),
        
        -- ไม้คลุมดิน
        ('supplier_026', 'plant_026', 'สวนไม้ประดับไทย', 160, '081-234-5678', 'กรุงเทพฯ', '30-40 ซม.'),
        ('supplier_027', 'plant_027', 'ร้านต้นไม้สวยงาม', 100, '082-345-6789', 'เชียงใหม่', '20-30 ซม.'),
        ('supplier_028', 'plant_028', 'สวนไม้ประดับไทย', 90, '081-234-5678', 'กรุงเทพฯ', '15-25 ซม.'),
        ('supplier_029', 'plant_029', 'ร้านต้นไม้สวยงาม', 120, '082-345-6789', 'เชียงใหม่', '25-35 ซม.'),
        ('supplier_030', 'plant_030', 'สวนไม้ประดับไทย', 160, '081-234-5678', 'กรุงเทพฯ', '30-40 ซม.')
      ON CONFLICT (id) DO NOTHING
    `);

    console.log('✅ Plants data added successfully!');
    console.log('Added: 20 more plants, 20 more suppliers');

  } catch (error) {
    console.error('❌ Adding plants failed:', error);
    throw error;
  } finally {
    await pool.end();
  }
}

// Run if called directly
if (require.main === module) {
  addPlants().catch(console.error);
}

module.exports = { addPlants };

const { Pool } = require('pg');

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

async function addTables() {
  try {
    console.log('Adding new tables...');

    // Create orders table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS orders (
        id VARCHAR(50) PRIMARY KEY,
        order_number VARCHAR(100) UNIQUE NOT NULL,
        total_amount DECIMAL(10,2) NOT NULL,
        status VARCHAR(50) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
      )
    `);

    // Create order_items table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS order_items (
        id VARCHAR(50) PRIMARY KEY,
        order_id VARCHAR(50) REFERENCES orders(id) ON DELETE CASCADE,
        plant_id VARCHAR(50) REFERENCES plants(id) ON DELETE CASCADE,
        supplier_id VARCHAR(50) REFERENCES suppliers(id) ON DELETE CASCADE,
        quantity INTEGER NOT NULL,
        unit_price DECIMAL(10,2) NOT NULL,
        total_price DECIMAL(10,2) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
      )
    `);

    // Create locations table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS locations (
        id VARCHAR(50) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        address TEXT,
        phone VARCHAR(20),
        created_at TIMESTAMP DEFAULT NOW()
      )
    `);

    // Insert sample locations
    await pool.query(`
      INSERT INTO locations (id, name, address, phone)
      VALUES 
        ('loc_001', 'กรุงเทพฯ', '123 ถนนสุขุมวิท กรุงเทพฯ 10110', '02-123-4567'),
        ('loc_002', 'เชียงใหม่', '456 ถนนนิมมานเหมินท์ เชียงใหม่ 50200', '053-123-4567')
      ON CONFLICT (id) DO NOTHING
    `);

    console.log('✅ Tables added successfully!');
    console.log('Created tables: orders, order_items, locations');
    console.log('Inserted sample data: 2 locations');

  } catch (error) {
    console.error('❌ Adding tables failed:', error);
    throw error;
  } finally {
    await pool.end();
  }
}

// Run if called directly
if (require.main === module) {
  addTables().catch(console.error);
}

module.exports = { addTables };

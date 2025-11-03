const { pool } = require('../database');
require('dotenv').config();

async function initSuppliersTable() {
  console.log('กำลังสร้างตาราง suppliers...');
  
  try {
    // สร้างตาราง suppliers ตาม schema ที่ใช้ใน server.js
    const query = `
      CREATE TABLE IF NOT EXISTS suppliers (
        id VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        location TEXT NOT NULL,
        phone VARCHAR(20),
        website VARCHAR(255),
        description TEXT,
        specialties TEXT DEFAULT '[]',
        business_hours VARCHAR(255),
        payment_methods TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
      )
    `;
    
    await pool.query(query);
    console.log('✅ สร้างตาราง suppliers สำเร็จ');
    
    // สร้าง index
    await pool.query('CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name)');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_suppliers_location ON suppliers(location)');
    console.log('✅ สร้าง index สำเร็จ');
    
    console.log('🎉 ตาราง suppliers พร้อมใช้งาน!');
    
    // ตรวจสอบจำนวนข้อมูล
    const countResult = await pool.query('SELECT COUNT(*) FROM suppliers');
    console.log(`📊 จำนวนข้อมูลปัจจุบัน: ${countResult.rows[0].count} รายการ`);
    
  } catch (error) {
    console.error('❌ เกิดข้อผิดพลาด:', error.message);
    console.error(error);
  } finally {
    await pool.end();
    process.exit();
  }
}

initSuppliersTable();


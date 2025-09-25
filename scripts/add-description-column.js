const { Pool } = require('pg');

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

async function addDescriptionColumn() {
  try {
    console.log('Adding description column to plants table...');

    // Add description column to plants table
    await pool.query(`
      ALTER TABLE plants 
      ADD COLUMN IF NOT EXISTS description TEXT
    `);

    console.log('✅ Description column added successfully!');

  } catch (error) {
    console.error('❌ Adding description column failed:', error);
    throw error;
  } finally {
    await pool.end();
  }
}

// Run if called directly
if (require.main === module) {
  addDescriptionColumn().catch(console.error);
}

module.exports = { addDescriptionColumn };

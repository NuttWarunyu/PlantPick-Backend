const { Pool } = require('pg');

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

// Test connection
pool.on('connect', () => {
  console.log('Connected to PostgreSQL database');
});

pool.on('error', (err) => {
  console.error('Database connection error:', err);
});

// Database queries
const db = {
  // Plants
  async getPlants() {
    const query = `
      SELECT p.id,
             p.name,
             p.scientific_name as "scientificName",
             p.category,
             p.plant_type as "plantType",
             p.measurement_type as "measurementType",
             p.created_at as "createdAt",
             p.updated_at as "updatedAt",
             COALESCE(
               json_agg(
                 json_build_object(
                   'id', s.id,
                   'name', s.name,
                   'price', s.price,
                   'phone', s.phone,
                   'location', s.location,
                   'lastUpdated', s.last_updated,
                   'size', s.size
                 )
               ) FILTER (WHERE s.id IS NOT NULL), 
               '[]'
             ) as suppliers
      FROM plants p
      LEFT JOIN suppliers s ON p.id = s.plant_id
      GROUP BY p.id, p.name, p.scientific_name, p.category, p.plant_type, p.measurement_type, p.created_at, p.updated_at
      ORDER BY p.name
    `;
    const result = await pool.query(query);
    return result.rows.map(row => ({
      ...row,
      hasSuppliers: row.suppliers.length > 0
    }));
  },

  async getPlantById(id) {
    const query = `
      SELECT p.id,
             p.name,
             p.scientific_name as "scientificName",
             p.category,
             p.plant_type as "plantType",
             p.measurement_type as "measurementType",
             p.created_at as "createdAt",
             p.updated_at as "updatedAt",
             COALESCE(
               json_agg(
                 json_build_object(
                   'id', s.id,
                   'name', s.name,
                   'price', s.price,
                   'phone', s.phone,
                   'location', s.location,
                   'lastUpdated', s.last_updated,
                   'size', s.size
                 )
               ) FILTER (WHERE s.id IS NOT NULL), 
               '[]'
             ) as suppliers
      FROM plants p
      LEFT JOIN suppliers s ON p.id = s.plant_id
      WHERE p.id = $1
      GROUP BY p.id, p.name, p.scientific_name, p.category, p.plant_type, p.measurement_type, p.created_at, p.updated_at
    `;
    const result = await pool.query(query, [id]);
    if (result.rows.length === 0) return null;
    
    const row = result.rows[0];
    return {
      ...row,
      hasSuppliers: row.suppliers.length > 0
    };
  },

  // Suppliers
  async addSupplier(plantId, supplierData) {
    const query = `
      INSERT INTO suppliers (id, plant_id, name, price, phone, location, size, last_updated)
      VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
      RETURNING *
    `;
    const result = await pool.query(query, [
      supplierData.id,
      plantId,
      supplierData.name,
      supplierData.price,
      supplierData.phone,
      supplierData.location,
      supplierData.size
    ]);
    return result.rows[0];
  },

  async updateSupplierPrice(plantId, supplierId, newPrice) {
    const query = `
      UPDATE suppliers 
      SET price = $1, last_updated = NOW()
      WHERE id = $2 AND plant_id = $3
      RETURNING *
    `;
    const result = await pool.query(query, [newPrice, supplierId, plantId]);
    return result.rows[0];
  },

  async deleteSupplier(plantId, supplierId) {
    const query = `
      DELETE FROM suppliers 
      WHERE id = $1 AND plant_id = $2
      RETURNING *
    `;
    const result = await pool.query(query, [supplierId, plantId]);
    return result.rows[0];
  }
};

module.exports = { pool, db };

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
  },

  // Orders
  async createOrder(orderData) {
    const query = `
      INSERT INTO orders (id, order_number, total_amount, status)
      VALUES ($1, $2, $3, $4)
      RETURNING *
    `;
    const result = await pool.query(query, [
      orderData.id,
      orderData.orderNumber,
      orderData.totalAmount,
      orderData.status || 'pending'
    ]);
    return result.rows[0];
  },

  async addOrderItem(orderId, itemData) {
    const query = `
      INSERT INTO order_items (id, order_id, plant_id, supplier_id, quantity, unit_price, total_price)
      VALUES ($1, $2, $3, $4, $5, $6, $7)
      RETURNING *
    `;
    const result = await pool.query(query, [
      itemData.id,
      orderId,
      itemData.plantId,
      itemData.supplierId,
      itemData.quantity,
      itemData.unitPrice,
      itemData.totalPrice
    ]);
    return result.rows[0];
  },

  async getOrders() {
    const query = `
      SELECT o.*, 
             COALESCE(
               json_agg(
                 json_build_object(
                   'id', oi.id,
                   'plantId', oi.plant_id,
                   'supplierId', oi.supplier_id,
                   'quantity', oi.quantity,
                   'unitPrice', oi.unit_price,
                   'totalPrice', oi.total_price
                 )
               ) FILTER (WHERE oi.id IS NOT NULL), 
               '[]'
             ) as items
      FROM orders o
      LEFT JOIN order_items oi ON o.id = oi.order_id
      GROUP BY o.id
      ORDER BY o.created_at DESC
    `;
    const result = await pool.query(query);
    return result.rows;
  },

  // Locations
  async getLocations() {
    const query = `SELECT * FROM locations ORDER BY name`;
    const result = await pool.query(query);
    return result.rows;
  },

  // Create new plant
  async createPlant(plantData) {
    const query = `
      INSERT INTO plants (id, name, scientific_name, category, plant_type, measurement_type, description)
      VALUES ($1, $2, $3, $4, $5, $6, $7)
      RETURNING *
    `;
    const result = await pool.query(query, [
      plantData.id,
      plantData.name,
      plantData.scientificName,
      plantData.category,
      plantData.plantType,
      plantData.measurementType,
      plantData.description
    ]);
    return result.rows[0];
  }
};

module.exports = { pool, db };

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const multer = require('multer');
const csv = require('csv-parser');
const { v4: uuidv4 } = require('uuid');
const { db, pool } = require('./database');
const aiService = require('./services/aiService');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3002;

// Middleware
app.use(helmet());
app.use(cors({
  origin: true, // Allow all origins for now
  credentials: true
}));
app.use(morgan('combined'));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Configure multer for file uploads
const upload = multer({ 
  dest: 'uploads/',
  limits: {
    fileSize: 10 * 1024 * 1024 // 10MB limit
  }
});

// Database connection will be handled by database.js

// Routes
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    message: 'Plant Price API is running',
    timestamp: new Date().toISOString()
  });
});

// Add supplier endpoint
app.post('/api/suppliers', async (req, res) => {
  try {
    const { name, location, phone, website, description, specialties, businessHours, paymentMethods } = req.body;
    
    const supplierId = `supplier_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const query = `
      INSERT INTO suppliers (id, name, location, phone, website, description, specialties, business_hours, payment_methods, created_at)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
      RETURNING *
    `;
    
    const result = await pool.query(query, [
      supplierId,
      name,
      location,
      phone || null,
      website || null,
      description || null,
      JSON.stringify(specialties),
      businessHours || null,
      JSON.stringify(paymentMethods)
    ]);
    
    res.json({
      success: true,
      data: result.rows[0],
      message: 'เพิ่มข้อมูลร้านค้าสำเร็จ'
    });
  } catch (error) {
    console.error('Error adding supplier:', error);
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการเพิ่มข้อมูลร้านค้า'
    });
  }
});

// Add plant-supplier connection
app.post('/api/plant-suppliers', async (req, res) => {
  try {
    const { plantId, supplierId, price, size, stockQuantity, minOrderQuantity, deliveryAvailable, deliveryCost, notes } = req.body;
    
    const connectionId = `ps_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const query = `
      INSERT INTO plant_suppliers (id, plant_id, supplier_id, price, size, stock_quantity, min_order_quantity, delivery_available, delivery_cost, notes)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
      RETURNING *
    `;
    
    const result = await pool.query(query, [
      connectionId,
      plantId,
      supplierId,
      price,
      size || null,
      stockQuantity || 0,
      minOrderQuantity || 1,
      deliveryAvailable || false,
      deliveryCost || 0,
      notes || null
    ]);
    
    res.json({
      success: true,
      data: result.rows[0],
      message: 'เพิ่มการเชื่อมต่อต้นไม้-ร้านค้าสำเร็จ'
    });
  } catch (error) {
    console.error('Error adding plant-supplier connection:', error);
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการเพิ่มการเชื่อมต่อ'
    });
  }
});

// Get plant-supplier connections
app.get('/api/plant-suppliers', async (req, res) => {
  try {
    const { plantId, supplierId } = req.query;
    
    let query = `
      SELECT 
        ps.*,
        p.name as plant_name,
        p.scientific_name as plant_scientific_name,
        p.category as plant_category,
        s.name as supplier_name,
        s.location as supplier_location,
        s.phone as supplier_phone
      FROM plant_suppliers ps
      JOIN plants p ON ps.plant_id = p.id
      JOIN suppliers s ON ps.supplier_id = s.id
      WHERE ps.is_active = true
    `;
    
    const params = [];
    if (plantId) {
      query += ` AND ps.plant_id = $${params.length + 1}`;
      params.push(plantId);
    }
    if (supplierId) {
      query += ` AND ps.supplier_id = $${params.length + 1}`;
      params.push(supplierId);
    }
    
    query += ` ORDER BY ps.price ASC`;
    
    const result = await pool.query(query, params);
    
    res.json({
      success: true,
      data: result.rows,
      message: 'ดึงข้อมูลการเชื่อมต่อสำเร็จ'
    });
  } catch (error) {
    console.error('Error getting plant-supplier connections:', error);
    res.status(500).json({
      success: false,
      data: [],
      message: 'เกิดข้อผิดพลาดในการดึงข้อมูลการเชื่อมต่อ'
    });
  }
});

// Get all suppliers
app.get('/api/suppliers', async (req, res) => {
  try {
    const query = `
      SELECT id, name, location, phone, website, description, 
             specialties, business_hours, payment_methods, created_at
      FROM suppliers
      ORDER BY created_at DESC
    `;
    
    const result = await pool.query(query);
    
    const suppliers = result.rows.map(row => {
      let specialties = [];
      let paymentMethods = [];
      
      // Handle specialties - check if it's valid JSON
      if (row.specialties && row.specialties.trim() !== '') {
        try {
          // Check if it's already an array or object
          if (typeof row.specialties === 'string') {
            if (row.specialties.startsWith('[') || row.specialties.startsWith('{')) {
              specialties = JSON.parse(row.specialties);
            } else {
              // If it's a comma-separated string, convert to array
              specialties = row.specialties.split(',').map(s => s.trim()).filter(s => s);
            }
          } else {
            specialties = row.specialties;
          }
        } catch (e) {
          console.error('Error parsing specialties:', e);
          // Fallback: treat as comma-separated string
          specialties = row.specialties.split(',').map(s => s.trim()).filter(s => s);
        }
      } else {
        specialties = [];
      }
      
      // Handle payment methods - check if it's valid JSON
      if (row.payment_methods && row.payment_methods.trim() !== '') {
        try {
          // Check if it's already an array or object
          if (typeof row.payment_methods === 'string') {
            if (row.payment_methods.startsWith('[') || row.payment_methods.startsWith('{')) {
              paymentMethods = JSON.parse(row.payment_methods);
            } else {
              // If it's a comma-separated string, convert to array
              paymentMethods = row.payment_methods.split(',').map(s => s.trim()).filter(s => s);
            }
          } else {
            paymentMethods = row.payment_methods;
          }
        } catch (e) {
          console.error('Error parsing paymentMethods:', e);
          // Fallback: treat as comma-separated string
          paymentMethods = row.payment_methods.split(',').map(s => s.trim()).filter(s => s);
        }
      } else {
        paymentMethods = [];
      }
      
      return {
        ...row,
        specialties,
        paymentMethods
      };
    });
    
    res.json({
      success: true,
      data: suppliers,
      message: 'ดึงข้อมูลร้านค้าสำเร็จ'
    });
  } catch (error) {
    console.error('Error getting suppliers:', error);
    res.status(500).json({
      success: false,
      data: [],
      message: `เกิดข้อผิดพลาดในการดึงข้อมูลร้านค้า: ${error.message}`
    });
  }
});

// Get statistics
app.get('/api/statistics', async (req, res) => {
  try {
    const plants = await db.getPlants();
    const suppliers = await db.getAllSuppliers();
    
    // นับจำนวนต้นไม้ตามหมวดหมู่
    const categoryCount = {};
    const plantTypeCount = {};
    
    plants.forEach(plant => {
      categoryCount[plant.category] = (categoryCount[plant.category] || 0) + 1;
      plantTypeCount[plant.plantType] = (plantTypeCount[plant.plantType] || 0) + 1;
    });
    
    res.json({
      success: true,
      data: {
        totalPlants: plants.length,
        totalSuppliers: suppliers.length,
        categoryCount,
        plantTypeCount
      },
      message: 'ดึงข้อมูลสถิติสำเร็จ'
    });
  } catch (error) {
    console.error('Error fetching statistics:', error);
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการดึงข้อมูลสถิติ'
    });
  }
});

// 📊 Statistics Endpoint - ดึงข้อมูลสถิติ
app.get('/statistics', async (req, res) => {
  try {
    const plants = await db.getPlants();
    const suppliers = await db.getAllSuppliers();
    
    // นับจำนวนต้นไม้ตามหมวดหมู่
    const categoryCount = {};
    const plantTypeCount = {};
    
    plants.forEach(plant => {
      categoryCount[plant.category] = (categoryCount[plant.category] || 0) + 1;
      plantTypeCount[plant.plant_type] = (plantTypeCount[plant.plant_type] || 0) + 1;
    });
    
    res.json({
      success: true,
      data: {
        totalPlants: plants.length,
        totalSuppliers: suppliers.length,
        categoryCount,
        plantTypeCount
      },
      message: 'ดึงข้อมูลสถิติสำเร็จ'
    });
  } catch (error) {
    console.error('Error fetching statistics:', error);
    res.status(500).json({
      success: false,
      data: {
        totalPlants: 0,
        totalSuppliers: 0,
        categoryCount: {},
        plantTypeCount: {}
      },
      message: 'เกิดข้อผิดพลาดในการดึงข้อมูลสถิติ'
    });
  }
});

// Get all plants
app.get('/api/plants', async (req, res) => {
  try {
    const plants = await db.getPlants();
    res.json({
      success: true,
      data: plants,
      message: 'ดึงข้อมูลต้นไม้สำเร็จ'
    });
  } catch (error) {
    console.error('Error fetching plants:', error);
    res.status(500).json({
      success: false,
      data: [],
      message: 'เกิดข้อผิดพลาดในการดึงข้อมูลต้นไม้'
    });
  }
});

// Get specific plant by ID
app.get('/api/plants/:id', async (req, res) => {
  try {
    const plant = await db.getPlantById(req.params.id);
    if (!plant) {
      return res.status(404).json({
        success: false,
        data: null,
        message: 'ไม่พบข้อมูลต้นไม้'
      });
    }
    
    res.json({
      success: true,
      data: plant,
      message: 'ดึงข้อมูลต้นไม้สำเร็จ'
    });
  } catch (error) {
    console.error('Error fetching plant:', error);
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการดึงข้อมูลต้นไม้'
    });
  }
});

// Add supplier to plant
app.post('/api/plants/:plantId/suppliers', async (req, res) => {
  try {
    const { plantId } = req.params;
    const { name, price, phone, location, size } = req.body;
    
    // Check if plant exists
    const plant = await db.getPlantById(plantId);
    if (!plant) {
      return res.status(404).json({
        success: false,
        data: null,
        message: 'ไม่พบข้อมูลต้นไม้'
      });
    }
    
    const newSupplier = {
      id: `supplier_${Date.now()}`,
      name,
      price: Number(price),
      phone,
      location,
      size
    };
    
    const supplier = await db.addSupplier(plantId, newSupplier);
    
    res.json({
      success: true,
      data: supplier,
      message: 'เพิ่มข้อมูลผู้จัดจำหน่ายสำเร็จ'
    });
  } catch (error) {
    console.error('Error adding supplier:', error);
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการเพิ่มข้อมูลผู้จัดจำหน่าย'
    });
  }
});

// Update supplier price
app.put('/api/plants/:plantId/suppliers/:supplierId/price', async (req, res) => {
  try {
    const { plantId, supplierId } = req.params;
    const { price } = req.body;
    
    const supplier = await db.updateSupplierPrice(plantId, supplierId, Number(price));
    if (!supplier) {
      return res.status(404).json({
        success: false,
        data: null,
        message: 'ไม่พบข้อมูลผู้จัดจำหน่าย'
      });
    }
    
    res.json({
      success: true,
      data: supplier,
      message: 'อัปเดตราคาสำเร็จ'
    });
  } catch (error) {
    console.error('Error updating supplier price:', error);
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการอัปเดตราคา'
    });
  }
});

// Delete supplier
app.delete('/api/plants/:plantId/suppliers/:supplierId', async (req, res) => {
  try {
    const { plantId, supplierId } = req.params;
    
    const supplier = await db.deleteSupplier(plantId, supplierId);
    if (!supplier) {
      return res.status(404).json({
        success: false,
        data: null,
        message: 'ไม่พบข้อมูลผู้จัดจำหน่าย'
      });
    }
    
    res.json({
      success: true,
      data: supplier,
      message: 'ลบข้อมูลผู้จัดจำหน่ายสำเร็จ'
    });
  } catch (error) {
    console.error('Error deleting supplier:', error);
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการลบข้อมูลผู้จัดจำหน่าย'
    });
  }
});

// 🤖 AI Endpoints

// AI Validation - ตรวจสอบข้อมูลด้วย AI
app.post('/api/ai/validate', async (req, res) => {
  try {
    const { data, type } = req.body;
    
    const validation = await aiService.validateDataWithAI(data, type);
    
    res.json({
      success: true,
      data: validation,
      message: 'ตรวจสอบข้อมูลสำเร็จ'
    });
  } catch (error) {
    console.error('AI Validation Error:', error);
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการตรวจสอบข้อมูล'
    });
  }
});

// AI Price Analysis - วิเคราะห์ราคาด้วย AI
app.post('/api/ai/analyze-price', async (req, res) => {
  try {
    const { plantName, price, category, historicalPrices } = req.body;
    
    // ใช้ AI วิเคราะห์ราคา
    const aiAnalysis = await aiService.analyzePrice(plantName, price, category);
    
    // ใช้ Smart Pricing
    const optimalPrice = aiService.suggestOptimalPrice(plantName, category, price, historicalPrices || []);
    
    res.json({
      success: true,
      data: {
        aiAnalysis,
        optimalPrice,
        timestamp: new Date().toISOString()
      },
      message: 'วิเคราะห์ราคาสำเร็จ'
    });
  } catch (error) {
    console.error('AI Price Analysis Error:', error);
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการวิเคราะห์ราคา'
    });
  }
});

// AI Business Insights - ดูข้อมูลเชิงลึก
app.get('/api/ai/insights', async (req, res) => {
  try {
    const plants = await db.getPlants();
    const suppliers = await db.getAllSuppliers();
    const orders = await db.getOrders();
    
    const insights = aiService.generateInsights(plants, suppliers, orders);
    
    res.json({
      success: true,
      data: insights,
      message: 'ดึงข้อมูลเชิงลึกสำเร็จ'
    });
  } catch (error) {
    console.error('AI Insights Error:', error);
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการดึงข้อมูลเชิงลึก'
    });
  }
});

// Orders
app.get('/api/orders', async (req, res) => {
  try {
    const orders = await db.getOrders();
    res.json({
      success: true,
      data: orders,
      message: 'ดึงข้อมูลคำสั่งซื้อสำเร็จ'
    });
  } catch (error) {
    console.error('Error fetching orders:', error);
    res.status(500).json({
      success: false,
      data: [],
      message: 'เกิดข้อผิดพลาดในการดึงข้อมูลคำสั่งซื้อ'
    });
  }
});

app.post('/api/orders', async (req, res) => {
  try {
    const { orderNumber, totalAmount, items } = req.body;
    
    const orderId = `order_${Date.now()}`;
    const order = await db.createOrder({
      id: orderId,
      orderNumber,
      totalAmount,
      status: 'pending'
    });
    
    // Add order items
    for (const item of items) {
      await db.addOrderItem(orderId, {
        id: `item_${Date.now()}_${Math.random()}`,
        plantId: item.plantId,
        supplierId: item.supplierId,
        quantity: item.quantity,
        unitPrice: item.unitPrice,
        totalPrice: item.totalPrice
      });
    }
    
    res.json({
      success: true,
      data: order,
      message: 'สร้างคำสั่งซื้อสำเร็จ'
    });
  } catch (error) {
    console.error('Error creating order:', error);
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการสร้างคำสั่งซื้อ'
    });
  }
});

// Locations
app.get('/api/locations', async (req, res) => {
  try {
    const locations = await db.getLocations();
    res.json({
      success: true,
      data: locations,
      message: 'ดึงข้อมูลที่ตั้งสำเร็จ'
    });
  } catch (error) {
    console.error('Error fetching locations:', error);
    res.status(500).json({
      success: false,
      data: [],
      message: 'เกิดข้อผิดพลาดในการดึงข้อมูลที่ตั้ง'
    });
  }
});

// Add new plant
app.post('/api/plants', async (req, res) => {
  try {
    const { name, scientificName, category, plantType, measurementType, description } = req.body;
    
    const plantId = `plant_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const plant = await db.createPlant({
      id: plantId,
      name,
      scientificName,
      category,
      plantType,
      measurementType,
      description
    });
    
    res.json({
      success: true,
      data: plant,
      message: 'เพิ่มข้อมูลต้นไม้สำเร็จ'
    });
  } catch (error) {
    console.error('Error creating plant:', error);
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการเพิ่มข้อมูลต้นไม้'
    });
  }
});

// Add supplier to plant
app.post('/api/plants/:plantId/suppliers', async (req, res) => {
  try {
    const { plantId } = req.params;
    const { name, price, phone, location, size } = req.body;
    
    const supplierId = `supplier_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const supplier = await db.addSupplier(plantId, {
      id: supplierId,
      name,
      price: Number(price),
      phone,
      location,
      size
    });
    
    res.json({
      success: true,
      data: supplier,
      message: 'เพิ่มข้อมูลผู้จัดจำหน่ายสำเร็จ'
    });
  } catch (error) {
    console.error('Error adding supplier:', error);
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการเพิ่มข้อมูลผู้จัดจำหน่าย'
    });
  }
});

// Bulk import plants from CSV
app.post('/api/plants/bulk-import', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        success: 0,
        failed: 0,
        errors: ['ไม่พบไฟล์ที่อัปโหลด']
      });
    }

    const fs = require('fs');
    const results = [];
    const errors = [];
    let successCount = 0;
    let failedCount = 0;

    // Read and parse CSV file
    fs.createReadStream(req.file.path)
      .pipe(csv())
      .on('data', (data) => {
        results.push(data);
      })
      .on('end', async () => {
        try {
          // Process each plant
          for (const plantData of results) {
            try {
              // Validate required fields
              if (!plantData.name || !plantData.category || !plantData.plantType || !plantData.measurementType) {
                errors.push(`ข้อมูลไม่ครบถ้วน: ${plantData.name || 'ไม่ระบุชื่อ'}`);
                failedCount++;
                continue;
              }

              const plantId = `plant_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
              const plant = await db.createPlant({
                id: plantId,
                name: plantData.name.trim(),
                scientificName: plantData.scientificName ? plantData.scientificName.trim() : '',
                category: plantData.category.trim(),
                plantType: plantData.plantType.trim(),
                measurementType: plantData.measurementType.trim(),
                description: plantData.description ? plantData.description.trim() : ''
              });

              successCount++;
            } catch (error) {
              errors.push(`ข้อผิดพลาดในการเพิ่ม ${plantData.name}: ${error.message}`);
              failedCount++;
            }
          }

          // Clean up uploaded file
          fs.unlinkSync(req.file.path);

          res.json({
            success: true,
            success: successCount,
            failed: failedCount,
            errors: errors
          });
        } catch (error) {
          console.error('Error processing CSV:', error);
          res.status(500).json({
            success: false,
            success: 0,
            failed: 0,
            errors: ['เกิดข้อผิดพลาดในการประมวลผลไฟล์']
          });
        }
      })
      .on('error', (error) => {
        console.error('Error reading CSV:', error);
        res.status(500).json({
          success: false,
          success: 0,
          failed: 0,
          errors: ['เกิดข้อผิดพลาดในการอ่านไฟล์ CSV']
        });
      });
  } catch (error) {
    console.error('Error in bulk import:', error);
    res.status(500).json({
      success: false,
      success: 0,
      failed: 0,
      errors: ['เกิดข้อผิดพลาดในการนำเข้าข้อมูล']
    });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    success: false,
    data: null,
    message: 'เกิดข้อผิดพลาดภายในเซิร์ฟเวอร์'
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    success: false,
    data: null,
    message: 'ไม่พบ API endpoint ที่ต้องการ'
  });
});

// Initialize database tables
async function initializeDatabase() {
  try {
    console.log('🔍 กำลังตรวจสอบและสร้างตาราง suppliers...');
    
    // สร้างตาราง suppliers ถ้ายังไม่มี
    await pool.query(`
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
    `);
    
    // สร้าง index
    await pool.query('CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name)');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_suppliers_location ON suppliers(location)');
    
    console.log('✅ ตาราง suppliers พร้อมใช้งาน');
    
    // ตรวจสอบจำนวนข้อมูล
    const countResult = await pool.query('SELECT COUNT(*) FROM suppliers');
    console.log(`📊 จำนวนร้านค้าในฐานข้อมูล: ${countResult.rows[0].count} รายการ`);
    
  } catch (error) {
    console.error('❌ เกิดข้อผิดพลาดในการสร้างตาราง:', error.message);
    // ไม่ throw error เพราะอาจมีตารางอยู่แล้ว
  }
}

// Start server
app.listen(PORT, async () => {
  console.log(`🌱 Plant Price API Server running on port ${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/api/health`);
  console.log(`🌿 Plants API: http://localhost:${PORT}/api/plants`);
  
  // Initialize database tables
  await initializeDatabase();
});

module.exports = app;

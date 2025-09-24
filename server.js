const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const { v4: uuidv4 } = require('uuid');
const { db } = require('./database');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(helmet());
app.use(cors({
  origin: true, // Allow all origins for now
  credentials: true
}));
app.use(morgan('combined'));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Database connection will be handled by database.js

// Routes
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    message: 'Plant Price API is running',
    timestamp: new Date().toISOString()
  });
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

// Start server
app.listen(PORT, () => {
  console.log(`🌱 Plant Price API Server running on port ${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/api/health`);
  console.log(`🌿 Plants API: http://localhost:${PORT}/api/plants`);
});

module.exports = app;

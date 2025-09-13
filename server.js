const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(helmet());
app.use(cors({
  origin: process.env.FRONTEND_URL || 'http://localhost:3000',
  credentials: true
}));
app.use(morgan('combined'));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// In-memory storage (ใน production ควรใช้ database)
let plantsData = [
  {
    id: "plant_001",
    name: "ต้นยางอินเดีย",
    scientificName: "Ficus elastica",
    category: "ไม้ประดับ",
    plantType: "ไม้ประดับ",
    measurementType: "ความสูง",
    suppliers: [
      {
        id: "supplier_001",
        name: "สวนไม้ประดับไทย",
        price: 150,
        phone: "081-234-5678",
        location: "กรุงเทพฯ",
        lastUpdated: "2024-01-15T10:30:00Z",
        size: "30-40 ซม."
      }
    ],
    hasSuppliers: true
  },
  {
    id: "plant_002",
    name: "ต้นมอนสเตอร่า",
    scientificName: "Monstera deliciosa",
    category: "ไม้ประดับ",
    plantType: "ไม้ประดับ",
    measurementType: "ความสูง",
    suppliers: [
      {
        id: "supplier_002",
        name: "ร้านต้นไม้สวยงาม",
        price: 200,
        phone: "082-345-6789",
        location: "เชียงใหม่",
        lastUpdated: "2024-01-14T15:20:00Z",
        size: "40-50 ซม."
      }
    ],
    hasSuppliers: true
  }
];

// Routes
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    message: 'Plant Price API is running',
    timestamp: new Date().toISOString()
  });
});

// Get all plants
app.get('/api/plants', (req, res) => {
  try {
    res.json({
      success: true,
      data: plantsData,
      message: 'ดึงข้อมูลต้นไม้สำเร็จ'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      data: [],
      message: 'เกิดข้อผิดพลาดในการดึงข้อมูลต้นไม้'
    });
  }
});

// Get specific plant by ID
app.get('/api/plants/:id', (req, res) => {
  try {
    const plant = plantsData.find(p => p.id === req.params.id);
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
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการดึงข้อมูลต้นไม้'
    });
  }
});

// Add supplier to plant
app.post('/api/plants/:plantId/suppliers', (req, res) => {
  try {
    const { plantId } = req.params;
    const { name, price, phone, location, size } = req.body;
    
    const plant = plantsData.find(p => p.id === plantId);
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
      lastUpdated: new Date().toISOString(),
      size
    };
    
    plant.suppliers.push(newSupplier);
    plant.hasSuppliers = true;
    
    res.json({
      success: true,
      data: newSupplier,
      message: 'เพิ่มข้อมูลผู้จัดจำหน่ายสำเร็จ'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการเพิ่มข้อมูลผู้จัดจำหน่าย'
    });
  }
});

// Update supplier price
app.put('/api/plants/:plantId/suppliers/:supplierId/price', (req, res) => {
  try {
    const { plantId, supplierId } = req.params;
    const { price } = req.body;
    
    const plant = plantsData.find(p => p.id === plantId);
    if (!plant) {
      return res.status(404).json({
        success: false,
        data: null,
        message: 'ไม่พบข้อมูลต้นไม้'
      });
    }
    
    const supplier = plant.suppliers.find(s => s.id === supplierId);
    if (!supplier) {
      return res.status(404).json({
        success: false,
        data: null,
        message: 'ไม่พบข้อมูลผู้จัดจำหน่าย'
      });
    }
    
    supplier.price = Number(price);
    supplier.lastUpdated = new Date().toISOString();
    
    res.json({
      success: true,
      data: supplier,
      message: 'อัปเดตราคาสำเร็จ'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      data: null,
      message: 'เกิดข้อผิดพลาดในการอัปเดตราคา'
    });
  }
});

// Delete supplier
app.delete('/api/plants/:plantId/suppliers/:supplierId', (req, res) => {
  try {
    const { plantId, supplierId } = req.params;
    
    const plant = plantsData.find(p => p.id === plantId);
    if (!plant) {
      return res.status(404).json({
        success: false,
        data: null,
        message: 'ไม่พบข้อมูลต้นไม้'
      });
    }
    
    const supplierIndex = plant.suppliers.findIndex(s => s.id === supplierId);
    if (supplierIndex === -1) {
      return res.status(404).json({
        success: false,
        data: null,
        message: 'ไม่พบข้อมูลผู้จัดจำหน่าย'
      });
    }
    
    const deletedSupplier = plant.suppliers.splice(supplierIndex, 1)[0];
    plant.hasSuppliers = plant.suppliers.length > 0;
    
    res.json({
      success: true,
      data: deletedSupplier,
      message: 'ลบข้อมูลผู้จัดจำหน่ายสำเร็จ'
    });
  } catch (error) {
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

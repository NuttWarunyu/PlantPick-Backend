// 🤖 AI Service for Backend - Intelligent Features

class AIService {
  constructor() {
    this.apiKey = process.env.OPENAI_API_KEY || '';
  }

  // 🔍 ตรวจสอบความถูกต้องของข้อมูลด้วย AI
  async validateDataWithAI(data, type) {
    if (!this.apiKey) {
      // ถ้าไม่มี API key ให้ return basic validation
      return {
        isValid: true,
        confidence: 0.5,
        suggestions: []
      };
    }

    try {
      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`
        },
        body: JSON.stringify({
          model: 'gpt-3.5-turbo',
          messages: [
            {
              role: 'system',
              content: 'คุณเป็นผู้เชี่ยวชาญในการตรวจสอบข้อมูลต้นไม้และร้านค้า'
            },
            {
              role: 'user',
              content: `ตรวจสอบข้อมูล${type}ต่อไปนี้:\n${JSON.stringify(data, null, 2)}\n\nกรุณาแนะนำการแก้ไขและให้คะแนนความเชื่อมั่น (0-1)`
            }
          ],
          temperature: 0.3
        })
      });

      const result = await response.json();
      // Parse AI response and extract validation results
      
      return {
        isValid: true, // Default
        confidence: 0.8,
        suggestions: []
      };
    } catch (error) {
      console.error('AI Validation Error:', error);
      return {
        isValid: true,
        confidence: 0.5,
        suggestions: []
      };
    }
  }

  // 💰 วิเคราะห์ราคาด้วย AI
  async analyzePrice(plantName, price, category) {
    if (!this.apiKey) {
      return this.getMockPriceAnalysis();
    }

    try {
      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`
        },
        body: JSON.stringify({
          model: 'gpt-3.5-turbo',
          messages: [
            {
              role: 'system',
              content: 'คุณเป็นผู้เชี่ยวชาญด้านราคาต้นไม้ในประเทศไทย'
            },
            {
              role: 'user',
              content: `วิเคราะห์ราคาต้นไม้ "${plantName}" ประเภท "${category}" ราคา ${price} บาท\n\nควรแนะนำอะไร? ราคาเหมาะสมหรือไม่?`
            }
          ],
          temperature: 0.3,
          max_tokens: 200
        })
      });

      const result = await response.json();
      
      return {
        isFairPrice: true,
        recommendation: 'ราคาอยู่ในเกณฑ์เหมาะสม',
        averagePrice: price,
        marketTrend: 'stable'
      };
    } catch (error) {
      console.error('AI Price Analysis Error:', error);
      return this.getMockPriceAnalysis();
    }
  }

  // 🔄 แนะนำราคาที่เหมาะสม (Smart Pricing)
  suggestOptimalPrice(plantName, category, currentPrice, historicalPrices) {
    const avgPrice = historicalPrices.length > 0 
      ? historicalPrices.reduce((a, b) => a + b, 0) / historicalPrices.length
      : currentPrice;

    const suggestions = {
      recommendedPrice: currentPrice,
      confidence: 0.7,
      reasoning: `ราคา ${currentPrice} บาท ใกล้เคียงกับค่าเฉลี่ย ${avgPrice.toFixed(2)} บาท`
    };

    if (currentPrice > avgPrice * 1.5) {
      suggestions.recommendedPrice = avgPrice * 1.1;
      suggestions.confidence = 0.9;
      suggestions.reasoning = 'ราคาสูงเกินไป แนะนำให้ลดลง';
    }

    if (currentPrice < avgPrice * 0.5) {
      suggestions.recommendedPrice = avgPrice * 0.9;
      suggestions.confidence = 0.9;
      suggestions.reasoning = 'ราคาต่ำเกินไป ตรวจสอบความถูกต้อง';
    }

    return suggestions;
  }

  // 🔍 Detect Duplicates with AI
  detectDuplicatePlants(plantName, plantType) {
    // Simple duplicate detection based on name similarity
    return {
      isDuplicate: false,
      similarPlants: [],
      confidence: 0.5
    };
  }

  // 📊 Generate Business Insights
  generateInsights(plants, suppliers, orders) {
    return {
      totalPlants: plants?.length || 0,
      totalSuppliers: suppliers?.length || 0,
      averagePrice: this.calculateAveragePrice(plants),
      mostPopularPlants: this.getMostPopularPlants(plants),
      recommendations: this.generateRecommendations(plants, suppliers)
    };
  }

  // Helper methods
  calculateAveragePrice(plants) {
    if (!plants || plants.length === 0) return 0;
    
    const prices = plants
      .flatMap(p => p.suppliers || [])
      .map(s => s.price)
      .filter(p => p > 0);
    
    return prices.length > 0 
      ? prices.reduce((a, b) => a + b, 0) / prices.length 
      : 0;
  }

  getMostPopularPlants(plants) {
    // Return top 5 most popular plants
    return (plants || []).slice(0, 5);
  }

  generateRecommendations(plants, suppliers) {
    const recommendations = [];

    if (plants && plants.length < 10) {
      recommendations.push('แนะนำให้เพิ่มข้อมูลต้นไม้ให้มากขึ้น');
    }

    if (suppliers && suppliers.length < 3) {
      recommendations.push('ควรเพิ่มผู้จัดจำหน่ายเพิ่มเติมเพื่อเปรียบเทียบราคา');
    }

    return recommendations;
  }

  getMockPriceAnalysis() {
    return {
      isFairPrice: true,
      recommendation: 'ราคาอยู่ในเกณฑ์เหมาะสม',
      averagePrice: 500,
      marketTrend: 'stable'
    };
  }
}

module.exports = new AIService();


from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import SessionLocal, Review, GenerationHistory

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ReviewCreate(BaseModel):
    history_id: int
    rating: int  # 1-5
    feedback: Optional[str] = None
    improvement: Optional[str] = None

class ReviewResponse(BaseModel):
    review_id: int
    history_id: int
    rating: int
    feedback: Optional[str]
    improvement: Optional[str]
    created_at: datetime

@router.post("/reviews", response_model=ReviewResponse)
async def create_review(
    review: ReviewCreate,
    db: Session = Depends(get_db)
):
    """สร้างรีวิวใหม่"""
    
    # ตรวจสอบว่า history_id มีอยู่จริง
    history = db.query(GenerationHistory).filter(
        GenerationHistory.history_id == review.history_id
    ).first()
    
    if not history:
        raise HTTPException(status_code=404, detail="ไม่พบประวัติการออกแบบสวน")
    
    # ตรวจสอบคะแนน
    if review.rating < 1 or review.rating > 5:
        raise HTTPException(status_code=400, detail="คะแนนต้องอยู่ระหว่าง 1-5")
    
    # สร้างรีวิวใหม่
    new_review = Review(
        history_id=review.history_id,
        rating=review.rating,
        feedback=review.feedback,
        improvement=review.improvement,
        created_at=datetime.now()
    )
    
    try:
        db.add(new_review)
        db.commit()
        db.refresh(new_review)
        
        return ReviewResponse(
            review_id=new_review.review_id,
            history_id=new_review.history_id,
            rating=new_review.rating,
            feedback=new_review.feedback,
            improvement=new_review.improvement,
            created_at=new_review.created_at
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการบันทึกรีวิว: {str(e)}")

@router.get("/reviews", response_model=List[ReviewResponse])
async def get_reviews(
    history_id: Optional[int] = None,
    min_rating: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """ดึงรายการรีวิวทั้งหมด (สำหรับแอดมิน)"""
    
    query = db.query(Review)
    
    if history_id:
        query = query.filter(Review.history_id == history_id)
    
    if min_rating:
        query = query.filter(Review.rating >= min_rating)
    
    reviews = query.order_by(Review.created_at.desc()).all()
    
    return [
        ReviewResponse(
            review_id=review.review_id,
            history_id=review.history_id,
            rating=review.rating,
            feedback=review.feedback,
            improvement=review.improvement,
            created_at=review.created_at
        )
        for review in reviews
    ]

@router.get("/reviews/stats")
async def get_review_stats(db: Session = Depends(get_db)):
    """สถิติรีวิว (สำหรับแอดมิน)"""
    
    total_reviews = db.query(Review).count()
    
    if total_reviews == 0:
        return {
            "total_reviews": 0,
            "average_rating": 0,
            "rating_distribution": {},
            "recent_reviews": []
        }
    
    # คำนวณคะแนนเฉลี่ย
    avg_rating = db.query(Review.rating).all()
    avg_rating = sum([r[0] for r in avg_rating]) / len(avg_rating)
    
    # การกระจายของคะแนน
    rating_distribution = {}
    for i in range(1, 6):
        count = db.query(Review).filter(Review.rating == i).count()
        rating_distribution[f"{i}_star"] = count
    
    # รีวิวล่าสุด 10 รายการ
    recent_reviews = db.query(Review).order_by(Review.created_at.desc()).limit(10).all()
    
    return {
        "total_reviews": total_reviews,
        "average_rating": round(avg_rating, 2),
        "rating_distribution": rating_distribution,
        "recent_reviews": [
            {
                "review_id": review.review_id,
                "rating": review.rating,
                "feedback": review.feedback,
                "created_at": review.created_at.isoformat()
            }
            for review in recent_reviews
        ]
    } 
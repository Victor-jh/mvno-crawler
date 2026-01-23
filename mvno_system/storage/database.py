from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# 데이터베이스 파일 경로
DB_PATH = "storage/mvno.db"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"

Base = declarative_base()

class CrawlLog(Base):
    __tablename__ = 'crawl_logs'
    
    id = Column(Integer, primary_key=True)
    platform = Column(String(50), nullable=False)
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(20))  # 'running', 'success', 'failed'
    items_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    plans = relationship("Plan", back_populates="crawl_log")

class Plan(Base):
    __tablename__ = 'plans'
    
    id = Column(Integer, primary_key=True)
    crawl_log_id = Column(Integer, ForeignKey('crawl_logs.id'))
    
    platform = Column(String(50))
    carrier = Column(String(100))
    plan_name = Column(String(200))
    price = Column(String(50))      # 원본 가격 문자열
    price_int = Column(Integer)     # 숫자형 변환 가격 (분석용)
    data_raw = Column(String(100))  # 데이터 문자열 (예: "11GB+일2GB+3Mbps")
    
    # 추가 상세 정보 (JSON으로 유연하게 저장)
    details = Column(JSON, nullable=True)
    
    url = Column(Text)
    screenshot_path = Column(Text)
    collected_at = Column(DateTime, default=datetime.now)
    
    crawl_log = relationship("CrawlLog", back_populates="plans")

# 엔진 및 세션 생성
engine = create_engine(DATABASE_URL, echo=False)

def init_db():
    """데이터베이스 테이블 생성"""
    Base.metadata.create_all(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

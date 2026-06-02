from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

from database import Base


class Product(Base):
    __tablename__ = "products"

    id                 = Column(Integer, primary_key=True, index=True)
    asin               = Column(String, unique=True, index=True)
    product_name       = Column(String)
    regret_percentage  = Column(Float)
    reviews_count      = Column(Integer)
    created_at         = Column(DateTime, default=datetime.utcnow)


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id                 = Column(Integer, primary_key=True, index=True)
    asin               = Column(String, unique=True, index=True)
    product_name       = Column(String)
    product_image      = Column(String, nullable=True)
    regret_percentage  = Column(Float)
    recommendation     = Column(String)
    analyzed_at        = Column(DateTime, default=datetime.utcnow)


class RequestedProduct(Base):
    __tablename__ = "requested_products"

    id            = Column(Integer, primary_key=True, index=True)
    asin          = Column(String, unique=True, index=True)
    requested_at  = Column(DateTime, default=datetime.utcnow)
    request_count = Column(Integer, default=1)

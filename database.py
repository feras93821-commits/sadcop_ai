from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, BigInteger, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class FuelPrice(Base):
    __tablename__ = 'fuel_prices'
    id = Column(Integer, primary_key=True)
    fuel_type = Column(String(50), unique=True, nullable=False)
    price_usd = Column(Float, default=0.0)
    price_syp = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ExchangeRate(Base):
    __tablename__ = 'exchange_rate'
    id = Column(Integer, primary_key=True)
    usd_to_syp = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Complaint(Base):
    __tablename__ = 'complaints'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    username = Column(String(100))
    full_name = Column(String(200))
    phone = Column(String(50))
    complaint_text = Column(Text, nullable=False)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    admin_notes = Column(Text)

class Database:
    def __init__(self, db_url=None, reset_tables=False):
        if db_url is None:
            db_url = os.getenv("DATABASE_URL", "sqlite:///spc_bot.db")
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        self.engine = create_engine(db_url)
        
        if reset_tables:
            self._reset_all_tables()
        else:
            self._fix_schema_if_needed()
        
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self._init_defaults()
    
    def _fix_schema_if_needed(self

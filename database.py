from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class FuelPrice(Base):
    __tablename__ = 'fuel_prices'
    
    id = Column(Integer, primary_key=True)
    fuel_type = Column(String(50), unique=True, nullable=False)  # بنزين, مازوت, غاز منزلي, غاز صناعي
    price_usd = Column(Float, default=0.0)
    price_syp = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ExchangeRate(Base):
    __tablename__ = 'exchange_rate'
    
    id = Column(Integer, primary_key=True)
    usd_to_syp = Column(Float, default=0.0)  # سعر صرف الدولار مقابل الليرة
    updated_at = Column(DateTime, default=datetime.utcnow)

class Complaint(Base):
    __tablename__ = 'complaints'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String(100))
    full_name = Column(String(200))
    phone = Column(String(50))
    complaint_text = Column(Text, nullable=False)
    status = Column(String(20), default='pending')  # pending, reviewed, resolved
    created_at = Column(DateTime, default=datetime.utcnow)
    admin_notes = Column(Text)

class Database:
    def __init__(self, db_url=None):
        if db_url is None:
            db_url = os.getenv("DATABASE_URL", "sqlite:///spc_bot.db")
            # Railway uses postgres:// but SQLAlchemy needs postgresql://
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Initialize default data if empty
        self._init_defaults()
    
    def _init_defaults(self):
        # Initialize fuel types if not exists
        fuel_types = ['بنزين', 'مازوت', 'غاز منزلي', 'غاز صناعي']
        for fuel in fuel_types:
            if not self.session.query(FuelPrice).filter_by(fuel_type=fuel).first():
                self.session.add(FuelPrice(fuel_type=fuel))
        
        # Initialize exchange rate if not exists
        if not self.session.query(ExchangeRate).first():
            self.session.add(ExchangeRate(usd_to_syp=1.0))
        
        self.session.commit()
    
    # Fuel Prices Methods
    def get_fuel_price(self, fuel_type):
        return self.session.query(FuelPrice).filter_by(fuel_type=fuel_type).first()
    
    def get_all_prices(self):
        return self.session.query(FuelPrice).all()
    
    def update_fuel_price(self, fuel_type, price_usd=None, price_syp=None):
        fuel = self.get_fuel_price(fuel_type)
        if fuel:
            if price_usd is not None:
                fuel.price_usd = price_usd
            if price_syp is not None:
                fuel.price_syp = price_syp
            fuel.updated_at = datetime.utcnow()
            self.session.commit()
            return True
        return False
    
    # Exchange Rate Methods
    def get_exchange_rate(self):
        return self.session.query(ExchangeRate).first()
    
    def update_exchange_rate(self, rate):
        ex = self.get_exchange_rate()
        if ex:
            ex.usd_to_syp = rate
            ex.updated_at = datetime.utcnow()
            self.session.commit()
            return True
        return False
    
    # Complaints Methods
    def add_complaint(self, user_id, username, full_name, phone, complaint_text):
        complaint = Complaint(
            user_id=user_id,
            username=username,
            full_name=full_name,
            phone=phone,
            complaint_text=complaint_text
        )
        self.session.add(complaint)
        self.session.commit()
        return complaint
    
    def get_all_complaints(self):
        return self.session.query(Complaint).order_by(Complaint.created_at.desc()).all()
    
    def get_complaint(self, complaint_id):
        return self.session.query(Complaint).filter_by(id=complaint_id).first()
    
    def update_complaint_status(self, complaint_id, status, admin_notes=None):
        complaint = self.get_complaint(complaint_id)
        if complaint:
            complaint.status = status
            if admin_notes:
                complaint.admin_notes = admin_notes
            self.session.commit()
            return True
        return False

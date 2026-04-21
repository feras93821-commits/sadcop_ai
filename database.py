from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from datetime import datetime

Base = declarative_base()

class FuelPrice(Base):
    __tablename__ = 'fuel_prices'
    id = Column(Integer, primary_key=True)
    fuel_type = Column(String(50), unique=True, nullable=False)
    price_usd = Column(Float, default=0)
    price_syp = Column(Float, default=0)
    price_syp_new = Column(Float, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ExchangeRate(Base):
    __tablename__ = 'exchange_rate'
    id = Column(Integer, primary_key=True)
    usd_to_syp = Column(Float, default=15000)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Complaint(Base):
    __tablename__ = 'complaints'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    username = Column(String(120))
    full_name = Column(String(200))
    phone = Column(String(50))
    complaint_text = Column(Text)
    status = Column(String(30), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)

class Database:
    def __init__(self, url):
        self.engine = create_engine(url, pool_pre_ping=True)
        self.Session = scoped_session(sessionmaker(bind=self.engine, autoflush=False, autocommit=False))
        Base.metadata.create_all(self.engine)
        self.seed()

    def session(self):
        return self.Session()

    def seed(self):
        s = self.session()
        try:
            if not s.query(ExchangeRate).first():
                s.add(ExchangeRate())
            for name in ['بنزين','مازوت','غاز منزلي','غاز صناعي']:
                if not s.query(FuelPrice).filter_by(fuel_type=name).first():
                    s.add(FuelPrice(fuel_type=name))
            s.commit()
        finally:
            s.close()

    def get_all_prices(self):
        s = self.session()
        try:
            return s.query(FuelPrice).order_by(FuelPrice.id.asc()).all()
        finally:
            s.close()

    def get_exchange_rate(self):
        s = self.session()
        try:
            return s.query(ExchangeRate).first()
        finally:
            s.close()

    def add_complaint(self, user_id, username, full_name, phone, text):
        s = self.session()
        try:
            row = Complaint(user_id=user_id, username=username, full_name=full_name, phone=phone, complaint_text=text)
            s.add(row)
            s.commit()
            s.refresh(row)
            return row
        finally:
            s.close()

    def get_all_complaints(self):
        s = self.session()
        try:
            return s.query(Complaint).order_by(Complaint.created_at.desc()).all()
        finally:
            s.close()

    def update_complaint_status(self, complaint_id, status):
        s = self.session()
        try:
            row = s.query(Complaint).filter_by(id=complaint_id).first()
            if row:
                row.status = status
                s.commit()
                return True
            return False
        finally:
            s.close()

    def update_exchange_rate(self, value):
        s = self.session()
        try:
            row = s.query(ExchangeRate).first()
            row.usd_to_syp = float(value)
            row.updated_at = datetime.utcnow()
            s.commit()
        finally:
            s.close()

    def update_fuel_price(self, fuel_type, price_syp):
        s = self.session()
        try:
            row = s.query(FuelPrice).filter_by(fuel_type=fuel_type).first()
            rate = s.query(ExchangeRate).first().usd_to_syp
            row.price_syp = float(price_syp)
            row.price_syp_new = round(float(price_syp)/100,2)
            row.price_usd = round(float(price_syp)/rate,2) if rate else 0
            row.updated_at = datetime.utcnow()
            s.commit()
        finally:
            s.close()

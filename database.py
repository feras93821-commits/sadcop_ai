from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, BigInteger, or_
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
    price_syp_new = Column(Float, default=0.0)
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

# الجدول الجديد للمحطات
class Station(Base):
    __tablename__ = 'stations'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    location = Column(String(500))
    area = Column(String(100)) # اللاذقية، جبلة، الحفة، القرداحة، الريف
    status = Column(String(100), default='تعمل')
    phone = Column(String(50))
    updated_at = Column(DateTime, default=datetime.utcnow)

class Database:
    def __init__(self, db_url="sqlite:///spc_bot.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self._seed_data()

    def _seed_data(self):
        # إضافة بيانات أولية للمحطات إذا كانت القائمة فارغة
        if self.session.query(Station).count() == 0:
            initial_stations = [
                Station(name="محطة حورية", location="شارع 14 رمضان، اللاذقية", area="المدينة", status="24 ساعة"),
                Station(name="شركة سادكوب", location="المنطقة الصناعية، اللاذقية", area="المدينة", status="24 ساعة"),
                Station(name="محطة الشاطئ", location="طريق المدينة الرياضية", area="المدينة", status="24 ساعة"),
                Station(name="محطة ميهوب 2", location="أوتوستراد جبلة - اللاذقية", area="جبلة"),
                Station(name="محطة وقود الحفة", location="مدينة الحفة", area="الحفة"),
                Station(name="محطة وقود القرداحة", location="مدينة القرداحة", area="القرداحة"),
                Station(name="محطة كرسانا", location="طريق كسب", area="الريف"),
                Station(name="محطة سيانو", location="ريف جبلة الشرقي", area="الريف")
            ]
            self.session.add_all(initial_stations)
            self.session.commit()

    def search_stations(self, query_text):
        try:
            # البحث في الاسم أو الموقع أو المنطقة
            search_filter = or_(
                Station.name.like(f"%{query_text}%"),
                Station.location.like(f"%{query_text}%"),
                Station.area.like(f"%{query_text}%")
            )
            return self.session.query(Station).filter(search_filter).all()
        except Exception as e:
            print(f"Search stations error: {e}")
            return []

    def get_fuel_price(self, fuel_type):
        return self.session.query(FuelPrice).filter_by(fuel_type=fuel_type).first()

    def get_all_prices(self):
        return self.session.query(FuelPrice).all()

    def add_complaint(self, user_id, username, full_name, phone, text):
        new_comp = Complaint(user_id=user_id, username=username, full_name=full_name, phone=phone, complaint_text=text)
        self.session.add(new_comp)
        self.session.commit()
        return new_comp

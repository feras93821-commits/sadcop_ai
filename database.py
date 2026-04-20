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
    user_id = Column(BigInteger, nullable=False)  # ← تغيير إلى BigInteger
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
        
        # التحقق من وجود الجدول القديم ونوع الأعمدة
        if reset_tables:
            self._reset_tables()
        else:
            self._check_and_fix_schema()
        
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self._init_defaults()
    
    def _check_and_fix_schema(self):
        """التحقق من مخطط قاعدة البيانات وإصلاحه إذا لزم الأمر"""
        try:
            inspector = inspect(self.engine)
            
            # التحقق من وجود جدول الشكاوى
            if 'complaints' in inspector.get_table_names():
                # التحقق من نوع عمود user_id
                columns = inspector.get_columns('complaints')
                user_id_column = next((c for c in columns if c['name'] == 'user_id'), None)
                
                if user_id_column and 'int' in str(user_id_column['type']).lower():
                    # إذا كان النوع Integer عادي (ليس BigInteger)، نحتاج لإعادة إنشاء الجدول
                    print("⚠️  جدول complaints يستخدم Integer. جاري إعادة إنشائه بـ BigInteger...")
                    self._reset_complaints_table()
                    
        except Exception as e:
            print(f"⚠️  خطأ في التحقق من المخطط: {e}")
    
    def _reset_complaints_table(self):
        """حذف وإعادة إنشاء جدول الشكاوى فقط"""
        try:
            # حفظ البيانات القديمة إذا أمكن
            old_complaints = []
            try:
                with self.engine.connect() as conn:
                    result = conn.execute("SELECT * FROM complaints")
                    old_complaints = [dict(row._mapping) for row in result]
            except:
                pass
            
            # حذف الجدول القديم
            Complaint.__table__.drop(self.engine, checkfirst=True)
            
            # إعادة إنشاء الجدول
            Complaint.__table__.create(self.engine)
            
            # استعادة البيانات القديمة إذا كانت صالحة
            if old_complaints:
                with self.engine.connect() as conn:
                    for complaint in old_complaints:
                        try:
                            # التأكد من أن user_id يتناسب مع BigInteger
                            if isinstance(complaint.get('user_id'), int) and complaint['user_id'] < 9223372036854775807:
                                conn.execute(
                                    Complaint.__table__.insert(),
                                    {
                                        'user_id': complaint['user_id'],
                                        'username': complaint.get('username'),
                                        'full_name': complaint.get('full_name'),
                                        'phone': complaint.get('phone'),
                                        'complaint_text': complaint.get('complaint_text'),
                                        'status': complaint.get('status', 'pending'),
                                        'created_at': complaint.get('created_at', datetime.utcnow()),
                                        'admin_notes': complaint.get('admin_notes')
                                    }
                                )
                        except Exception as e:
                            print(f"⚠️  تخطي استعادة شكوى {complaint.get('id')}: {e}")
                    conn.commit()
            
            print("✅ تم إعادة إنشاء جدول complaints بنجاح بـ BigInteger!")
            
        except Exception as e:
            print(f"❌ خطأ في إعادة إنشاء الجدول: {e}")
            # إذا فشلت الاستعادة، نحذف وننشئ فقط
            Complaint.__table__.drop(self.engine, checkfirst=True)
            Complaint.__table__.create(self.engine)
    
    def _reset_tables(self):
        """حذف وإعادة إنشاء جميع الجداول (يحذف جميع البيانات!)"""
        print("⚠️  جاري حذف وإعادة إنشاء جميع الجداول...")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        print("✅ تم إعادة إنشاء جميع الجداول!")
    
    def _init_defaults(self):
        """تهيئة البيانات الافتراضية"""
        fuel_types = ['بنزين', 'مازوت', 'غاز منزلي', 'غاز صناعي']
        for fuel in fuel_types:
            if not self.session.query(FuelPrice).filter_by(fuel_type=fuel).first():
                self.session.add(FuelPrice(fuel_type=fuel))
        
        if not self.session.query(ExchangeRate).first():
            self.session.add(ExchangeRate(usd_to_syp=1.0))
        
        self.session.commit()
    
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
    
    def add_complaint(self, user_id, username, full_name, phone, complaint_text):
        """إضافة شكوى جديدة مع معالجة الأخطاء"""
        try:
            complaint = Complaint(
                user_id=int(user_id),  # التأكد من أنه رقم صحيح
                username=username,
                full_name=full_name,
                phone=phone,
                complaint_text=complaint_text
            )
            self.session.add(complaint)
            self.session.commit()
            return complaint
        except Exception as e:
            self.session.rollback()
            print(f"❌ خطأ في إضافة الشكوى: {e}")
            raise e
    
    def get_all_complaints(self):
        return self.session.query(Complaint).order_by(Complaint.created_at.desc()).all()
    
    def get_complaint(self, complaint_id):
        return self.session.query(Complaint).filter_by(id=complaint_id).first()
    
    def update_complaint_status(self, complaint_id, status, admin_notes=None):
        """تحديث حالة الشكوى"""
        try:
            complaint = self.get_complaint(complaint_id)
            if complaint:
                complaint.status = status
                if admin_notes:
                    complaint.admin_notes = admin_notes
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ خطأ في تحديث الشكوى: {e}")
            raise e

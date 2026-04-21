from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, BigInteger, inspect, event
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

class Database:
    def __init__(self, db_url=None, reset_tables=False):
        if db_url is None:
            db_url = os.getenv("DATABASE_URL")
            
            if not db_url:
                print("ERROR: DATABASE_URL not set!")
                raise ValueError("DATABASE_URL environment variable is required")
            
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            
            if "postgresql://" in db_url and "psycopg2" not in db_url:
                db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        
        print(f"Database URL: {db_url[:50]}...")
        
        try:
            self.engine = create_engine(
                db_url,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={"connect_timeout": 10}
            )
            
            with self.engine.connect() as conn:
                print("Database connection successful!")
            
        except Exception as e:
            print(f"Database connection failed: {e}")
            raise e
        
        if reset_tables:
            self._reset_all_tables()
        else:
            self._fix_schema_if_needed()
        
        try:
            Base.metadata.create_all(self.engine)
            print("Tables created successfully!")
        except Exception as e:
            print(f"Error creating tables: {e}")
            raise e
        
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self._init_defaults()
    
    def _fix_schema_if_needed(self):
        try:
            inspector = inspect(self.engine)
            
            if 'complaints' in inspector.get_table_names():
                columns = inspector.get_columns('complaints')
                user_id_col = next((c for c in columns if c['name'] == 'user_id'), None)
                
                if user_id_col:
                    col_type = str(user_id_col['type']).lower()
                    if 'integer' in col_type and 'big' not in col_type:
                        print("Fixing complaints table: Integer -> BigInteger")
                        self._reset_complaints_table()
                        
        except Exception as e:
            print(f"Schema check warning: {e}")
    
    def _reset_complaints_table(self):
        try:
            old_data = []
            try:
                with self.engine.connect() as conn:
                    result = conn.execute("SELECT * FROM complaints")
                    old_data = [dict(row._mapping) for row in result]
            except:
                pass
            
            Complaint.__table__.drop(self.engine, checkfirst=True)
            Complaint.__table__.create(self.engine)
            
            if old_data:
                with self.engine.connect() as conn:
                    for row in old_data:
                        try:
                            conn.execute(
                                Complaint.__table__.insert(),
                                {
                                    'user_id': row.get('user_id'),
                                    'username': row.get('username'),
                                    'full_name': row.get('full_name'),
                                    'phone': row.get('phone'),
                                    'complaint_text': row.get('complaint_text'),
                                    'status': row.get('status', 'pending'),
                                    'created_at': row.get('created_at', datetime.utcnow()),
                                    'admin_notes': row.get('admin_notes')
                                }
                            )
                        except Exception as e:
                            print(f"Skipping row: {e}")
                    conn.commit()
            
            print("Complaints table recreated with BigInteger")
            
        except Exception as e:
            print(f"Reset error: {e}")
            Complaint.__table__.drop(self.engine, checkfirst=True)
            Complaint.__table__.create(self.engine)
    
    def _reset_all_tables(self):
        print("Resetting all tables...")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        print("All tables recreated")
    
    def _init_defaults(self):
        try:
            fuel_types = ['بنزين', 'مازوت', 'غاز منزلي', 'غاز صناعي']
            for fuel in fuel_types:
                if not self.session.query(FuelPrice).filter_by(fuel_type=fuel).first():
                    self.session.add(FuelPrice(fuel_type=fuel, price_usd=0.0, price_syp=0.0, price_syp_new=0.0))
            
            if not self.session.query(ExchangeRate).first():
                self.session.add(ExchangeRate(usd_to_syp=15000.0))
            
            self.session.commit()
            print("Default data initialized")
        except Exception as e:
            print(f"Error initializing defaults: {e}")
            self.session.rollback()
    
    def get_fuel_price(self, fuel_type):
        try:
            return self.session.query(FuelPrice).filter_by(fuel_type=fuel_type).first()
        except Exception as e:
            print(f"Error getting fuel price: {e}")
            return None
    
    def get_all_prices(self):
        try:
            return self.session.query(FuelPrice).all()
        except Exception as e:
            print(f"Error getting all prices: {e}")
            return []
    
       def update_fuel_price(self, fuel_type, price_usd=None, price_syp=None, price_syp_new=None):
        """تحديث سعر الوقود - يحسب العملة الجديدة تلقائياً (قسمة على 100)"""
        try:
            fuel = self.get_fuel_price(fuel_type)
            if fuel:
                if price_usd is not None:
                    fuel.price_usd = price_usd
                if price_syp is not None:
                    fuel.price_syp = price_syp
                    # ✅ حساب العملة الجديدة تلقائياً: حذف صفرين
                    fuel.price_syp_new = round(float(price_syp) / 100.0, 2)
                elif price_syp_new is not None:
                    fuel.price_syp_new = price_syp_new
                
                fuel.updated_at = datetime.utcnow()
                self.session.commit()
                print(f"Price updated for {fuel_type}: USD={fuel.price_usd}, SYP_OLD={fuel.price_syp}, SYP_NEW={fuel.price_syp_new}")
                return True
            else:
                print(f"Fuel type not found: {fuel_type}")
            return False
        except Exception as e:
            print(f"Error updating fuel price: {e}")
            self.session.rollback()
            return False
    
    def get_exchange_rate(self):
        try:
            rate = self.session.query(ExchangeRate).first()
            if not rate:
                rate = ExchangeRate(usd_to_syp=15000.0)
                self.session.add(rate)
                self.session.commit()
                print("Default exchange rate created: 15000")
            return rate
        except Exception as e:
            print(f"Error getting exchange rate: {e}")
            self.session.rollback()
            return ExchangeRate(usd_to_syp=15000.0)
    
    def update_exchange_rate(self, rate):
        try:
            ex = self.get_exchange_rate()
            if ex:
                ex.usd_to_syp = rate
                ex.updated_at = datetime.utcnow()
                self.session.commit()
                print(f"Exchange rate updated to {rate}")
                return True
            return False
        except Exception as e:
            print(f"Error updating exchange rate: {e}")
            self.session.rollback()
            return False
    
    def add_complaint(self, user_id, username, full_name, phone, complaint_text):
        try:
            complaint = Complaint(
                user_id=int(user_id),
                username=username,
                full_name=full_name,
                phone=phone,
                complaint_text=complaint_text
            )
            self.session.add(complaint)
            self.session.commit()
            print(f"Complaint added with ID: {complaint.id}")
            return complaint
        except Exception as e:
            self.session.rollback()
            print(f"Add complaint error: {e}")
            raise e
    
    def get_all_complaints(self):
        try:
            return self.session.query(Complaint).order_by(Complaint.created_at.desc()).all()
        except Exception as e:
            print(f"Error getting complaints: {e}")
            return []
    
    def get_complaint(self, complaint_id):
        try:
            return self.session.query(Complaint).filter_by(id=complaint_id).first()
        except Exception as e:
            print(f"Error getting complaint: {e}")
            return None
    
    def update_complaint_status(self, complaint_id, status, admin_notes=None):
        try:
            complaint = self.get_complaint(complaint_id)
            if complaint:
                complaint.status = status
                if admin_notes:
                    complaint.admin_notes = admin_notes
                self.session.commit()
                print(f"Complaint {complaint_id} status updated to {status}")
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"Update status error: {e}")
            raise e

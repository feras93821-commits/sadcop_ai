from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    BigInteger,
    text
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from datetime import datetime

Base = declarative_base()


# =========================
# Models
# =========================

class FuelPrice(Base):
    __tablename__ = "fuel_prices"

    id = Column(Integer, primary_key=True)
    fuel_type = Column(String(50), unique=True, nullable=False)

    price_usd = Column(Float, default=0)
    price_syp = Column(Float, default=0)
    price_syp_new = Column(Float, default=0)

    updated_at = Column(DateTime, default=datetime.utcnow)


class ExchangeRate(Base):
    __tablename__ = "exchange_rate"

    id = Column(Integer, primary_key=True)
    usd_to_syp = Column(Float, default=15000)

    updated_at = Column(DateTime, default=datetime.utcnow)


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)

    username = Column(String(120))
    full_name = Column(String(200))
    phone = Column(String(50))

    complaint_text = Column(Text)
    status = Column(String(30), default="pending")

    created_at = Column(DateTime, default=datetime.utcnow)


# =========================
# Database Manager
# =========================

class Database:
    def __init__(self, url):
        self.engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_recycle=300
        )

        self.Session = scoped_session(
            sessionmaker(
                bind=self.engine,
                autoflush=False,
                autocommit=False
            )
        )

        # إنشاء الجداول
        Base.metadata.create_all(self.engine)

        # ترقية الجداول القديمة
        self.migrate()

        # إدخال البيانات الأساسية
        self.seed()

    # =========================
    # Session Helper
    # =========================
    def session(self):
        return self.Session()

    # =========================
    # Migration
    # =========================
    def migrate(self):
        with self.engine.connect() as conn:
            try:
                # PostgreSQL / Railway
                conn.execute(text("""
                    ALTER TABLE fuel_prices
                    ADD COLUMN IF NOT EXISTS price_syp_new FLOAT DEFAULT 0
                """))

                conn.execute(text("""
                    ALTER TABLE fuel_prices
                    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP
                """))

                conn.execute(text("""
                    ALTER TABLE exchange_rate
                    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP
                """))

                conn.commit()
                print("✅ Database migration completed")

            except Exception as e:
                print("⚠️ Migration skipped:", e)

    # =========================
    # Seed Default Data
    # =========================
    def seed(self):
        s = self.session()

        try:
            if not s.query(ExchangeRate).first():
                s.add(ExchangeRate())

            fuels = [
                "بنزين",
                "مازوت",
                "غاز منزلي",
                "غاز صناعي"
            ]

            for fuel in fuels:
                row = s.query(FuelPrice).filter_by(
                    fuel_type=fuel
                ).first()

                if not row:
                    s.add(FuelPrice(fuel_type=fuel))

            s.commit()
            print("✅ Seed completed")

        except Exception as e:
            s.rollback()
            print("❌ Seed error:", e)

        finally:
            s.close()

    # =========================
    # Prices
    # =========================
    def get_all_prices(self):
        s = self.session()
        try:
            return s.query(FuelPrice).order_by(FuelPrice.id.asc()).all()
        finally:
            s.close()

    def get_fuel_price(self, fuel_type):
        s = self.session()
        try:
            return s.query(FuelPrice).filter_by(
                fuel_type=fuel_type
            ).first()
        finally:
            s.close()

    def update_fuel_price(self, fuel_type, price_syp):
        s = self.session()

        try:
            row = s.query(FuelPrice).filter_by(
                fuel_type=fuel_type
            ).first()

            if not row:
                return False

            rate = s.query(ExchangeRate).first()

            exchange = rate.usd_to_syp if rate else 15000

            row.price_syp = float(price_syp)
            row.price_syp_new = round(float(price_syp) / 100, 2)
            row.price_usd = round(float(price_syp) / exchange, 2)
            row.updated_at = datetime.utcnow()

            s.commit()
            return True

        except Exception as e:
            s.rollback()
            print("❌ update_fuel_price:", e)
            return False

        finally:
            s.close()

    # =========================
    # Exchange Rate
    # =========================
    def get_exchange_rate(self):
        s = self.session()
        try:
            row = s.query(ExchangeRate).first()

            if not row:
                row = ExchangeRate()
                s.add(row)
                s.commit()

            return row

        finally:
            s.close()

    def update_exchange_rate(self, value):
        s = self.session()

        try:
            row = s.query(ExchangeRate).first()

            if not row:
                row = ExchangeRate()

            row.usd_to_syp = float(value)
            row.updated_at = datetime.utcnow()

            s.add(row)
            s.commit()
            return True

        except Exception as e:
            s.rollback()
            print("❌ update_exchange_rate:", e)
            return False

        finally:
            s.close()

    # =========================
    # Complaints
    # =========================
    def add_complaint(
        self,
        user_id,
        username,
        full_name,
        phone,
        complaint_text
    ):
        s = self.session()

        try:
            row = Complaint(
                user_id=user_id,
                username=username,
                full_name=full_name,
                phone=phone,
                complaint_text=complaint_text
            )

            s.add(row)
            s.commit()
            s.refresh(row)

            return row

        except Exception as e:
            s.rollback()
            print("❌ add_complaint:", e)
            raise e

        finally:
            s.close()

    def get_all_complaints(self):
        s = self.session()
        try:
            return s.query(Complaint).order_by(
                Complaint.created_at.desc()
            ).all()
        finally:
            s.close()

    def update_complaint_status(self, complaint_id, status):
        s = self.session()

        try:
            row = s.query(Complaint).filter_by(
                id=complaint_id
            ).first()

            if not row:
                return False

            row.status = status
            s.commit()
            return True

        except Exception as e:
            s.rollback()
            print("❌ update_complaint_status:", e)
            return False

        finally:
            s.close()

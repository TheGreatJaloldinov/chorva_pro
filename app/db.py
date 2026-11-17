from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, Float, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from app.config import DATABASE_URL

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Animal(Base):
    __tablename__ = "animals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    kind: Mapped[str] = mapped_column(String(30))
    breed: Mapped[str] = mapped_column(String(100), default="")
    sex: Mapped[str] = mapped_column(String(20), default="")
    age_months: Mapped[int] = mapped_column(Integer, default=0)
    current_weight: Mapped[float] = mapped_column(Float, default=0)
    purchase_date: Mapped[str] = mapped_column(String(20), default="")
    purchase_price: Mapped[float] = mapped_column(Float, default=0)
    photo_file_id: Mapped[str] = mapped_column(String(300), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "code", name="uq_animal_user_code"),)

class WeightRecord(Base):
    __tablename__ = "weight_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), index=True)
    weight: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    note: Mapped[str] = mapped_column(Text, default="")

class FeedType(Base):
    __tablename__ = "feed_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    low_stock_alert: Mapped[float] = mapped_column(Float, default=10)
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_feed_user_name"),)

class FeedLot(Base):
    __tablename__ = "feed_lots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    feed_type_id: Mapped[int] = mapped_column(ForeignKey("feed_types.id"), index=True)
    purchased_at: Mapped[str] = mapped_column(String(20))
    quantity_initial: Mapped[float] = mapped_column(Float)
    quantity_remaining: Mapped[float] = mapped_column(Float)
    unit_price: Mapped[float] = mapped_column(Float)
    supplier: Mapped[str] = mapped_column(String(200), default="")

class FeedingSchedule(Base):
    __tablename__ = "feeding_schedules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), index=True)
    times_json: Mapped[str] = mapped_column(Text)
    items_json: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class FeedingReminder(Base):
    __tablename__ = "feeding_reminders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("feeding_schedules.id"), index=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), index=True)
    scheduled_for: Mapped[str] = mapped_column(String(30), unique=True)
    items_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    animal_id: Mapped[int | None] = mapped_column(ForeignKey("animals.id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(100))
    amount: Mapped[float] = mapped_column(Float)
    expense_date: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text, default="")

class Income(Base):
    __tablename__ = "incomes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    animal_id: Mapped[int | None] = mapped_column(ForeignKey("animals.id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(100))
    amount: Mapped[float] = mapped_column(Float)
    income_date: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text, default="")

class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Telegram user IDs can exceed PostgreSQL INTEGER (int32). Upgrade
        # existing installations in-place without deleting user data.
        if engine.dialect.name == "postgresql":
            await conn.execute(text(
                "ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT"
            ))

async def get_user(session: AsyncSession, telegram_id: int, full_name: str = "") -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, full_name=full_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user

class BackupLog(Base):
    __tablename__ = "backup_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    backup_date: Mapped[str] = mapped_column(String(20))
    __table_args__ = (UniqueConstraint("user_id", "backup_date", name="uq_backup_user_date"),)


class FeedUsage(Base):
    __tablename__ = "feed_usages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    animal_id: Mapped[int | None] = mapped_column(ForeignKey("animals.id"), nullable=True, index=True)
    feed_type_id: Mapped[int] = mapped_column(ForeignKey("feed_types.id"), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    used_at: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text, default="")

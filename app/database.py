from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class DailyReading(Base):
    __tablename__ = "daily_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    mac_address: Mapped[str] = mapped_column(String, index=True)
    data: Mapped[dict] = mapped_column(JSON)


class MonthlyAggregate(Base):
    __tablename__ = "monthly_aggregates"

    id: Mapped[int] = mapped_column(primary_key=True)
    mac_address: Mapped[str] = mapped_column(String, index=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    metric_name: Mapped[str] = mapped_column(String)
    min_value: Mapped[float] = mapped_column(Float)
    max_value: Mapped[float] = mapped_column(Float)
    avg_value: Mapped[float] = mapped_column(Float)
    count: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("mac_address", "year", "month", "metric_name"),
    )


class YearlyAggregate(Base):
    __tablename__ = "yearly_aggregates"

    id: Mapped[int] = mapped_column(primary_key=True)
    mac_address: Mapped[str] = mapped_column(String, index=True)
    year: Mapped[int] = mapped_column(Integer)
    metric_name: Mapped[str] = mapped_column(String)
    min_value: Mapped[float] = mapped_column(Float)
    max_value: Mapped[float] = mapped_column(Float)
    avg_value: Mapped[float] = mapped_column(Float)
    count: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("mac_address", "year", "metric_name"),
    )


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

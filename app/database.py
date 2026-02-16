from datetime import datetime

from sqlalchemy import DateTime, JSON, String, UniqueConstraint, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class DailyReading(Base):
    __tablename__ = "daily_readings"
    __table_args__ = (
        UniqueConstraint("timestamp", "mac_address", name="uq_timestamp_mac"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    mac_address: Mapped[str] = mapped_column(String, index=True)
    data: Mapped[dict] = mapped_column(JSON)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # For existing databases: deduplicate rows and create unique index if missing
    async with engine.begin() as conn:
        # Remove duplicates keeping the row with the highest id for each (timestamp, mac_address)
        await conn.execute(text("""
            DELETE FROM daily_readings
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM daily_readings
                GROUP BY timestamp, mac_address
            )
        """))
        # Create unique index if it doesn't already exist
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_timestamp_mac "
            "ON daily_readings (timestamp, mac_address)"
        ))


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

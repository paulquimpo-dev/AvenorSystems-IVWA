from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
import config

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default='admin')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    credential_mode: Mapped[str] = mapped_column(String(20), default='vulnerable')
    session_version: Mapped[int] = mapped_column(Integer, default=1)

def database():
    config.validate()
    engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
    return engine, sessionmaker(engine, expire_on_commit=False)

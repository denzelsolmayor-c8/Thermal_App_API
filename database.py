from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.automap import automap_base
from typing import AsyncGenerator
# administrator:helios@helios-configdb:5432/helios
# administrator:helios@10.147.18.242:5433/helios

DATABASE_URL = "postgresql+asyncpg://administrator:helios@helios-configdb:5432/helios"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = automap_base()


async def prepare_base():
    async with engine.begin() as conn:
        await conn.run_sync(Base.prepare, reflect=True)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from routes import upload_file_data, get_data, update_data
from routes import egress_endpoints_routes
from routes import schedule_routes
from routes import data_selector_routes
from routes import configuration_routes
from routes import combined_data_routes  # NEW: Import the new router

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi import FastAPI, Depends  # Consolidated FastAPI imports
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import AsyncSessionLocal, prepare_base, Base


# Reflect DB structure at startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    await prepare_base()
    yield


# Original FastAPI instance, now with lifespan
app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_file_data.router)
app.include_router(get_data.router)
app.include_router(update_data.router)
app.include_router(egress_endpoints_routes.router)
app.include_router(schedule_routes.router)
app.include_router(data_selector_routes.router)
app.include_router(configuration_routes.router)
app.include_router(combined_data_routes.router)  # NEW: Include the new router


@app.get("/")
def read_root():
    return {"Hello": "World"}

# Provide DB session per request


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


NODE_RED_URL = "http://10.147.18.242:1880/thermal-data"


@app.get("/camera-data")
async def camera_data():
    async with httpx.AsyncClient() as client:
        resp = await client.get(NODE_RED_URL, timeout=5.0)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code,
                            detail="Node-RED error")
    return resp.json()


# Example route to read any table by name
@app.get("/data/{table_name}")
async def read_table(table_name: str, db: AsyncSession = Depends(get_db)):
    try:
        TableClass = Base.classes[table_name]
    except KeyError:
        return {"error": f"Table '{table_name}' not found in the database."}

    result = await db.execute(select(TableClass))
    rows = result.scalars().all()

    return [dict(row.__dict__) for row in rows if "__sa_instance_state" not in row.__dict__]

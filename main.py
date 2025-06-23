from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from routes import upload_file_data, get_data
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi import FastAPI, Depends, HTTPException
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import AsyncSessionLocal, prepare_base, Base


# Reflect DB structure at startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    await prepare_base()
    yield


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


@app.get("/")
def read_root():
    return {"Hello": "World"}

# Provide DB session per request


NODE_RED_URL = "http://10.147.18.242:1880/thermal-data"


@app.get("/camera-data")
async def camera_data():
    async with httpx.AsyncClient() as client:
        resp = await client.get(NODE_RED_URL, timeout=5.0)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code,
                            detail="Node-RED error")
    return resp.json()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

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


# # 2ND OPTION for NodeRED real time updates
# # If your Node‑RED is already publishing messages (e.g. sensor readings) to an MQTT broker,
# # you can have FastAPI subscribe in the background and cache the latest values.

# # from fastapi import FastAPI
# # import threading
# # import paho.mqtt.client as mqtt

# # app = FastAPI()
# # latest_data = {}

# # def on_message(client, userdata, msg):
# #     # msg.topic == "sensors/temperature"
# #     latest_data[msg.topic] = msg.payload.decode()

# # def mqtt_thread():
# #     client = mqtt.Client()
# #     client.on_message = on_message
# #     client.connect("localhost", 1883)
# #     client.subscribe("sensors/#")
# #     client.loop_forever()

# # @app.on_event("startup")
# # def start_mqtt():
# #     thread = threading.Thread(target=mqtt_thread, daemon=True)
# #     thread.start()

# # @app.get("/mqtt-data/{topic}")
# # def get_mqtt_data(topic: str):
# #     key = f"sensors/{topic}"
# #     return { "topic": key, "value": latest_data.get(key) }

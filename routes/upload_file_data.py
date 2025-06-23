from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import Base, get_async_session

router = APIRouter()

# Input models


class SheetData(BaseModel):
    sheet_name: str
    headers: List[str]
    data: List[List[Any]]
    created_at: str


class UploadPayload(BaseModel):
    id: str
    filename: str
    sheets: List[SheetData]


def get_model_mapping():
    return {
        "camera_configs": Base.classes.camera_configs,
        "camera_in_zone": Base.classes.camera_in_zone,
        "camera_presets": Base.classes.camera_presets,
        "zones": Base.classes.zones,
        "customer": Base.classes.customer,
        "temperatures": Base.classes.temperatures,
    }


insert_order = [
    "zones",
    "camera_configs",
    "camera_presets",
    "camera_in_zone",
    "customer",
    "temperatures",
]


@router.post("/api/upload-file-data")
async def upload_file_data(payload: UploadPayload, session: AsyncSession = Depends(get_async_session)):
    result: Dict[str, List[Dict[str, Any]]] = {
        key: [] for key in get_model_mapping().keys()}

    for sheet in payload.sheets:
        for row in sheet.data:
            row_dict = dict(zip(sheet.headers, row))

            desc = row_dict.get("description", "")
            if isinstance(desc, str) and "alarm" in desc.lower():
                continue

            for table_name, model in get_model_mapping().items():
                required_cols = set(model.__table__.columns.keys())
                entry = {k: v for k, v in row_dict.items()
                         if k in required_cols}

                # allow optional rel_id
                if set(entry.keys()) >= required_cols - {"rel_id"}:
                    result[table_name].append(entry)

    model_mapping = get_model_mapping()

    for table_name in insert_order:
        entries = result.get(table_name, [])
        if not entries:
            continue

        model = model_mapping[table_name]

        # Explicit type conversions before bulk insert
        for entry in entries:
            try:
                if table_name == "camera_presets":
                    entry["preset_number"] = int(entry["preset_number"])
                elif table_name == "camera_in_zone":
                    entry["preset_number"] = int(
                        entry.get("preset_number", 0))  # optional
                elif table_name == "temperature" and "measurement" in entry:
                    entry["measurement"] = float(entry["measurement"])
            except Exception as e:
                print(f"[WARN] Skipping row due to conversion error: {entry}")
                print(e)

        try:
           # Bulk insert with conflict ignore
            stmt = pg_insert(model).values(entries).on_conflict_do_nothing()
            await session.execute(stmt)

        except Exception as e:
            print(f"[ERROR] Bulk insert failed for {table_name}")
            print(e)

    await session.commit()

    return {"message": "Upload complete", "record_count": {k: len(v) for k, v in result.items()}}

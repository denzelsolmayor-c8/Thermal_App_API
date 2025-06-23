from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import Base, get_async_session

router = APIRouter()


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
async def upload_file_data(
    payload: UploadPayload,
    session: AsyncSession = Depends(get_async_session)
):
    models = get_model_mapping()
    # prepare a buffer for each table
    result: Dict[str, List[Dict[str, Any]]] = {name: [] for name in models}

    # 1) COLUMN-BASED ROUTING: for each row, try to match it to each table
    for sheet in payload.sheets:
        for row in sheet.data:
            row_dict = dict(zip(sheet.headers, row))

            # skip alarms
            desc = row_dict.get("description", "")
            if isinstance(desc, str) and "alarm" in desc.lower():
                continue

            # try every table
            for table_name, model in models.items():
                cols = set(model.__table__.columns.keys())
                # Remove any auto-generated PK column names:
                non_auto = cols - {"rel_id", "id"}

                entry = {k: v for k, v in row_dict.items() if k in cols}
                if non_auto.issubset(entry.keys()):
                    result[table_name].append(entry)

    # 2) BULK INSERT each table in dependency order
    for table_name in insert_order:
        entries = result.get(table_name)
        if not entries:
            continue
        model = models[table_name]

        # type conversions
        for e in entries:
            if table_name in ("camera_presets", "camera_in_zone"):
                if "preset_number" in e:
                    e["preset_number"] = int(e["preset_number"])
            if table_name == "temperatures":
                e["point_in_preset"] = int(e["point_in_preset"])
                # preset_number too
                e["preset_number"] = int(e["preset_number"])

        try:
            stmt = pg_insert(model).values(entries).on_conflict_do_nothing()
            await session.execute(stmt)
        except Exception as exc:
            print(f"[ERROR] {table_name} bulk insert failed:", exc)

    # commit once
    try:
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(500, f"Commit failed: {exc}")

    return {
        "message": "Upload complete",
        "record_count": {t: len(v) for t, v in result.items()}
    }

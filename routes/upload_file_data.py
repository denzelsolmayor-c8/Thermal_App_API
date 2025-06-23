from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert

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


# Header-to-database mapping
header_mapping = {
    "camera_configs": {
        "camera_id": "Camera ID",
        "camera_ip": "Camera IP",
        "camera_name": "Camera Name",
        "camera_location": "Camera Location",
        "camera_type": "Camera Type",
        "brand": "Brand",
        "model": "Model",
        "firmware_version": "Firmware Version",
    },
    "camera_in_zone": {
        "camera_id": "Camera ID",
        "zone_id": "Zone ID",
    },
    "camera_presets": {
        "preset_number": "Preset Number",
        "camera_id": "Camera ID",
    },
    "zones": {
        "zone_id": "Zone ID",
        "zone_name": "Zone Name",
    },
    "customer": {
        "client_id": "Client ID",
        "client_name": "Client Name",
        "camera_id": "Camera ID",
    }
}

# Automapped table references


def get_model_mapping():
    return {
        "camera_configs": Base.classes.camera_configs,
        "camera_in_zone": Base.classes.camera_in_zone,
        "camera_presets": Base.classes.camera_presets,
        "zones": Base.classes.zones,
        "customer": Base.classes.customer,
    }


insert_order = ["zones", "camera_configs",
                "camera_presets", "camera_in_zone", "customer"]


@router.post("/api/upload-file-data")
async def upload_file_data(payload: UploadPayload, session: AsyncSession = Depends(get_async_session)):
    result: Dict[str, List[Dict[str, Any]]] = {
        key: [] for key in header_mapping.keys()}

    for sheet in payload.sheets:
        for row in sheet.data:
            row_dict = dict(zip(sheet.headers, row))

            # Optional filter: skip rows with 'Alarm' in description
            desc = row_dict.get("DESCRIPTION(V1)", "")
            if isinstance(desc, str) and "alarm" in desc.lower():
                continue

            for table_name, mappings in header_mapping.items():
                entry = {}
                missing_field = False

                for db_col, header_name in mappings.items():
                    value = row_dict.get(header_name)
                    if value is None:
                        missing_field = True
                        break
                    entry[db_col] = value

                if not missing_field:
                    result[table_name].append(entry)
    model_mapping = get_model_mapping()

    # Upload to database
    for table_name in insert_order:
        entries = result.get(table_name, [])
        if not entries:
            continue

        model = model_mapping[table_name]

        for entry in entries:
            try:
                # Explicit type conversions per table
                if table_name == "camera_presets":
                    entry["preset_number"] = int(entry["preset_number"])
                elif table_name == "camera_in_zone":
                    entry["preset_number"] = int(
                        entry["preset_number"])  # if it exists there too

                stmt = insert(model).values(**entry)
                await session.execute(stmt)

            except Exception as e:
                print(f"[ERROR] Failed to insert into {table_name}: {entry}")
                print(e)

    await session.commit()

    return {"message": "Upload complete", "record_count": {k: len(v) for k, v in result.items()}}

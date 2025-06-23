from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Any, Dict, Optional
from datetime import datetime
from collections import defaultdict

from database import get_async_session

router = APIRouter()

# ─── Response Schemas ──────────────────────────────────────────────────────────


class SheetDataOut(BaseModel):
    sheet_name: str
    headers: List[str]
    data: List[List[Any]]
    created_at: str


class DownloadPayload(BaseModel):
    sheets: List[SheetDataOut]


# ─── Helper: Group rows by zone_id ────────────────────────────────────────────

def build_payload_grouped_by_zone(rows, headers: List[str]) -> DownloadPayload:
    now = datetime.utcnow().isoformat()
    grouped: Dict[str, SheetDataOut] = defaultdict(lambda: SheetDataOut(
        sheet_name="", headers=headers, data=[], created_at=now
    ))

    for row in rows:
        row_dict = row._mapping
        sheet_name = row_dict.get("zone_id", "Unknown_Zone")

        if not grouped[sheet_name].sheet_name:
            grouped[sheet_name].sheet_name = sheet_name

        grouped[sheet_name].data.append([row_dict.get(h) for h in headers])

    return DownloadPayload(sheets=list(grouped.values()))


# ─── 1) Fixed‐SQL Endpoint ─────────────────────────────────────────────────────

@router.get("/api/data/fixed", response_model=DownloadPayload)
async def data_fixed(
    session: AsyncSession = Depends(get_async_session),
):
    headers = [
        "camera_id", "camera_ip", "camera_name", "camera_location",
        "camera_type", "brand", "model", "firmware_version",
        "zone_id", "zone_name", "preset_number",
        "temperature_id", "measurement", "description", "point_in_preset",
        "client_id", "client_name"
    ]

    sql = text("""
        SELECT DISTINCT
            cc.camera_id,
            cc.camera_ip,
            cc.camera_name,
            cc.camera_location,
            cc.camera_type,
            cc.brand,
            cc.model,
            cc.firmware_version,

            z.zone_id,
            z.zone_name,

            cp.preset_number,

            t.id AS temperature_id,
            t.measurement,
            t.description,
            t.point_in_preset,

            c.client_id,
            c.client_name

            FROM camera_configs cc

            -- Trust only valid camera + zone pairs
            LEFT JOIN camera_in_zone cz ON cc.camera_id = cz.camera_id
            LEFT JOIN zones z ON cz.zone_id = z.zone_id

            -- Join camera presets and their temperatures
            LEFT JOIN camera_presets cp ON cc.camera_id = cp.camera_id
            LEFT JOIN temperatures t ON cp.preset_number = t.preset_number

            -- Join customer table
            LEFT JOIN customer c ON cc.camera_id = c.camera_id;



    """)
    result = await session.execute(sql)
    rows = result.fetchall()
    return build_payload_grouped_by_zone(rows, headers)


# ─── 2) Dynamic‐Filters Endpoint ───────────────────────────────────────────────

@router.get("/api/data", response_model=DownloadPayload)
async def data_dynamic(
    camera_ip: Optional[str] = Query(None),
    preset_number: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    headers = [
        "camera_id", "camera_ip", "camera_name", "camera_location",
        "camera_type", "brand", "model", "firmware_version",
        "zone_id", "zone_name", "preset_number",
        "temperature_id", "measurement", "description", "point_in_preset",
        "client_id", "client_name"
    ]

    where_clauses = []
    params: Dict[str, Any] = {}

    if camera_ip:
        where_clauses.append("cc.camera_ip = :camera_ip")
        params["camera_ip"] = camera_ip
    if preset_number is not None:
        where_clauses.append("cp.preset_number = :preset_number")
        params["preset_number"] = preset_number

    # Ensure core data is present
    non_nulls = [
        "cc.camera_id", "cc.camera_ip", "cc.camera_name", "cc.camera_location",
        "cc.camera_type", "cc.brand", "cc.model", "cc.firmware_version",
        "z.zone_id", "z.zone_name", "cp.preset_number",
        "t.id", "t.measurement", "t.description", "t.point_in_preset",
        "c.client_id", "c.client_name"
    ]
    where_clauses += [f"{col} IS NOT NULL" for col in non_nulls]

    where_sql = " AND ".join(where_clauses)

    sql = text(f"""
        SELECT DISTINCT
            cc.camera_id,
            cc.camera_ip,
            cc.camera_name,
            cc.camera_location,
            cc.camera_type,
            cc.brand,
            cc.model,
            cc.firmware_version,

            z.zone_id,
            z.zone_name,

            cp.preset_number,

            t.id AS temperature_id,
            t.measurement,
            t.description,
            t.point_in_preset,

            c.client_id,
            c.client_name
        FROM camera_configs cc
        LEFT JOIN camera_in_zone cz ON cc.camera_id = cz.camera_id
        LEFT JOIN zones z ON cz.zone_id = z.zone_id
        LEFT JOIN camera_presets cp ON cc.camera_id = cp.camera_id
        LEFT JOIN temperatures t ON cp.preset_number = t.preset_number
        LEFT JOIN customer c ON cc.camera_id = c.camera_id
        WHERE {where_sql}
    """)

    result = await session.execute(sql, params)
    rows = result.fetchall()
    return build_payload_grouped_by_zone(rows, headers)

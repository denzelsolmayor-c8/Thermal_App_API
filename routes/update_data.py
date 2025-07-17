from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import text, select, update

from database import Base, get_async_session

router = APIRouter()

# --- Pydantic Models for Request Body ---


class SheetData(BaseModel):
    sheet_name: str
    headers: List[str]
    data: List[List[Any]]
    updated_at: Optional[str] = None


class UpdateFileRequest(BaseModel):
    sheets: List[SheetData]

# --- Helper functions ---


def get_model_mapping():
    """Returns a dictionary mapping table names to their SQLAlchemy ORM classes."""
    return {
        "camera_configs": Base.classes.camera_configs,
        "camera_in_zone": Base.classes.camera_in_zone,
        "camera_presets": Base.classes.camera_presets,
        "zones": Base.classes.zones,
        "customer": Base.classes.customer,
        "temperatures": Base.classes.temperatures,
    }


# Order of insertion/update to respect foreign key dependencies
insert_order = [
    "customer",
    "zones",
    "camera_configs",
    "camera_presets",
    "camera_in_zone",
    "temperatures",
]

# --- FastAPI Endpoint ---


@router.put("/api/data/update")
async def update_file_data(
    request: UpdateFileRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Updates file data in the database.
    Receives flattened data from the frontend and performs upserts
    into respective database tables. Uses batching for efficiency
    where possible, and per-record manual upserts for specific tables
    due to schema constraints.
    """
    models = get_model_mapping()
    updated_record_counts: Dict[str, int] = {name: 0 for name in models}

    # Prepare data for upsert operations, grouped by table
    data_to_process: Dict[str, List[Dict[str, Any]]] = {
        name: [] for name in models}

    try:
        for sheet in request.sheets:
            print(f"[DEBUG] Processing sheet for update: {sheet.sheet_name}")

            if not sheet.updated_at:
                sheet.updated_at = datetime.utcnow().isoformat()

            for row_list in sheet.data:
                row_dict = dict(zip(sheet.headers, row_list))

                # Extract and prepare data for each table, with type conversions

                # Customer
                customer_data = {
                    "client_id": row_dict.get("client_id"),
                    "client_name": row_dict.get("client_name"),
                }
                if customer_data.get("client_id") is not None:
                    data_to_process["customer"].append(customer_data)

                # Zones
                zone_data = {
                    "zone_id": row_dict.get("zone_id"),
                    "zone_name": row_dict.get("zone_name"),
                }
                if zone_data.get("zone_id") is not None:
                    data_to_process["zones"].append(zone_data)

                # Camera Configs
                camera_config_data = {
                    "camera_id": row_dict.get("camera_id"),
                    "camera_ip": row_dict.get("camera_ip"),
                    "camera_name": row_dict.get("camera_name"),
                    "camera_location": row_dict.get("camera_location"),
                    "camera_type": row_dict.get("camera_type"),
                    "brand": row_dict.get("brand"),
                    "model": row_dict.get("model"),
                    "firmware_version": row_dict.get("firmware_version"),
                    "client_id": row_dict.get("client_id"),
                }
                if camera_config_data.get("camera_id") is not None:
                    data_to_process["camera_configs"].append(
                        camera_config_data)

                # Camera Presets
                try:
                    preset_number = int(row_dict["preset_number"]) if row_dict.get(
                        "preset_number") not in [None, ''] else None
                except (ValueError, TypeError):
                    preset_number = None

                camera_id_for_preset = row_dict.get("camera_id")
                if camera_id_for_preset is not None and preset_number is not None:
                    camera_preset_data = {
                        "camera_id": camera_id_for_preset,
                        "preset_number": preset_number,
                    }
                    data_to_process["camera_presets"].append(
                        camera_preset_data)

                # Camera In Zone
                camera_id_for_zone = row_dict.get("camera_id")
                zone_id_for_zone = row_dict.get("zone_id")
                if camera_id_for_zone is not None and zone_id_for_zone is not None:
                    camera_in_zone_data = {
                        "camera_id": camera_id_for_zone,
                        "zone_id": zone_id_for_zone,
                    }
                    data_to_process["camera_in_zone"].append(
                        camera_in_zone_data)

                # Temperatures
                try:
                    temperature_id = int(row_dict["temperature_id"]) if row_dict.get(
                        "temperature_id") not in [None, ''] else None
                except (ValueError, TypeError):
                    temperature_id = None

                measurement_val = row_dict.get("measurement")
                measurement = measurement_val if measurement_val != '' else None

                try:
                    point_in_preset = int(row_dict["point_in_preset"]) if row_dict.get(
                        "point_in_preset") not in [None, ''] else None
                except (ValueError, TypeError):
                    point_in_preset = None

                temperature_data = {
                    "id": temperature_id,
                    "measurement": measurement,
                    "measurement_type": row_dict.get("measurement_type"),
                    "description": row_dict.get("description"),
                    "point_in_preset": point_in_preset,
                    "preset_number": preset_number,
                }
                if temperature_data.get("id") is not None:
                    data_to_process["temperatures"].append(temperature_data)

        # Remove duplicates within each table's data_to_process list
        for table_name in data_to_process:
            if table_name == "camera_presets":
                unique_data = {
                    (d.get("camera_id"), d.get("preset_number")): d
                    for d in data_to_process[table_name]
                }.values()
            elif table_name == "camera_in_zone":
                unique_data = {
                    (d.get("camera_id"), d.get("zone_id")): d
                    for d in data_to_process[table_name]
                }.values()
            elif table_name == "temperatures":
                unique_data = {
                    d.get("id"): d for d in data_to_process[table_name]}.values()
            elif table_name == "customer":
                unique_data = {
                    d.get("client_id"): d for d in data_to_process[table_name]}.values()
            elif table_name == "zones":
                unique_data = {
                    d.get("zone_id"): d for d in data_to_process[table_name]}.values()
            elif table_name == "camera_configs":
                unique_data = {
                    d.get("camera_id"): d for d in data_to_process[table_name]}.values()
            else:
                unique_data = data_to_process[table_name]

            data_to_process[table_name] = list(unique_data)

        # Perform upsert operations in dependency order
        for table_name in insert_order:
            entries = data_to_process.get(table_name)
            if not entries:
                print(
                    f"[DEBUG] Skipping upsert for '{table_name}' — no entries to update/insert.")
                continue

            model = models[table_name]

            if table_name in ["camera_presets", "camera_in_zone", "temperatures"]:
                # --- BATCHED/MANUAL UPSERT LOGIC FOR TABLES WITHOUT UNIQUE CONSTRAINTS ---

                if table_name == "camera_presets":
                    # Per-record manual upsert for camera_presets due to its PK(preset_number)
                    for entry in entries:
                        try:
                            existing_stmt = select(model).where(
                                model.preset_number == entry["preset_number"])
                            existing_record = (await session.execute(existing_stmt)).scalar_one_or_none()

                            if existing_record:
                                update_values = {
                                    k: v for k, v in entry.items() if v is not None}
                                if "camera_id" in entry and entry["camera_id"] is not None:
                                    update_values["camera_id"] = entry["camera_id"]

                                if update_values:
                                    update_stmt = update(model).where(
                                        model.preset_number == entry["preset_number"]
                                    ).values(update_values)
                                    await session.execute(update_stmt)
                                    print(
                                        f"[DEBUG] Updated existing record in '{table_name}': {entry}")
                                else:
                                    print(
                                        f"[DEBUG] No non-None values to update for existing record in '{table_name}': {entry}. Skipping update.")
                            else:
                                insert_stmt = pg_insert(model).values(entry)
                                await session.execute(insert_stmt)
                                print(
                                    f"[DEBUG] Inserted new record into '{table_name}': {entry}")
                            updated_record_counts[table_name] += 1
                        except Exception as exc:
                            print(
                                f"[ERROR] Manual upsert for {table_name} failed for entry {entry}: {exc}")
                            raise HTTPException(
                                status_code=500, detail=f"Database upsert failed for {table_name}: {exc}")

                elif table_name == "camera_in_zone":
                    # Batch insert for camera_in_zone (relying on unique_data filtering for uniqueness)
                    if entries:
                        try:
                            insert_stmt = pg_insert(model).values(entries)
                            await session.execute(insert_stmt)
                            print(
                                f"[DEBUG] Batch inserted into '{table_name}': {len(entries)} rows")
                            updated_record_counts[table_name] += len(entries)
                        except Exception as exc:
                            print(
                                f"[ERROR] Batch insert for '{table_name}' failed: {exc}")
                            raise HTTPException(
                                status_code=500, detail=f"Database insert failed for {table_name}: {exc}")

                elif table_name == "temperatures":
                    inserts_only_batch = []
                    updates_batch_statements = []  # Store update statements here

                    # 1. Fetch all existing records by ID in one go
                    keys_to_check = [e["id"]
                                     for e in entries if e.get("id") is not None]
                    if not keys_to_check:
                        continue
                    existing_records_query = select(
                        model).where(model.id.in_(keys_to_check))
                    existing_results = (await session.execute(existing_records_query)).scalars().all()
                    existing_records_dict = {
                        rec.id: rec for rec in existing_results}

                    # 2. Categorize into inserts and updates, and prepare update statements
                    for entry in entries:
                        if entry.get("id") in existing_records_dict:
                            existing_record_obj = existing_records_dict[entry["id"]]
                            update_values = {}
                            for k, v in entry.items():
                                if k == 'id':
                                    continue
                                if v is not None and v != '':  # If incoming value is not None/empty, use it
                                    update_values[k] = v
                                elif hasattr(existing_record_obj, k) and getattr(existing_record_obj, k) is not None:
                                    # If incoming is None/empty, but existing has a value, retain existing
                                    update_values[k] = getattr(
                                        existing_record_obj, k)

                            if update_values:
                                updates_batch_statements.append(update(model).where(
                                    model.id == entry["id"]).values(update_values))
                            else:
                                print(
                                    f"[DEBUG] No changes for existing temperature record: {entry}")
                        else:
                            # New record to insert
                            if entry.get("id") is not None:
                                inserts_only_batch.append(entry)
                            else:
                                print(
                                    f"[WARNING] Skipping insert for '{table_name}' due to missing ID: {entry}")

                    # 3. Execute batch inserts
                    if inserts_only_batch:
                        try:
                            insert_stmt = pg_insert(
                                model).values(inserts_only_batch)
                            await session.execute(insert_stmt)
                            print(
                                f"[DEBUG] Batch inserted into '{table_name}': {len(inserts_only_batch)} rows")
                            updated_record_counts[table_name] += len(
                                inserts_only_batch)
                        except Exception as exc:
                            print(
                                f"[ERROR] Batch insert for '{table_name}' failed: {exc}")
                            raise HTTPException(
                                status_code=500, detail=f"Database insert failed for {table_name}: {exc}")

                    # 4. Execute batch updates
                    if updates_batch_statements:
                        try:
                            for stmt in updates_batch_statements:
                                await session.execute(stmt)
                            print(
                                f"[DEBUG] Executed batch updates for '{table_name}': {len(updates_batch_statements)} rows")
                            updated_record_counts[table_name] += len(
                                updates_batch_statements)
                        except Exception as exc:
                            print(
                                f"[ERROR] Batch update for '{table_name}' failed: {exc}")
                            raise HTTPException(
                                status_code=500, detail=f"Database update failed for {table_name}: {exc}")

            # customer, zones, camera_configs (use ON CONFLICT DO UPDATE)
            else:
                on_conflict_target = []
                if table_name == "customer":
                    on_conflict_target = ["client_id"]
                elif table_name == "zones":
                    on_conflict_target = ["zone_id"]
                elif table_name == "camera_configs":
                    on_conflict_target = ["camera_id"]
                else:
                    print(
                        f"[WARNING] No conflict target defined for table: {table_name}. Skipping upsert.")
                    continue

                cols_to_update = {
                    col.name: getattr(pg_insert(model).excluded, col.name)
                    for col in model.__table__.columns
                    if col.name not in on_conflict_target and not col.primary_key
                }

                if not cols_to_update:
                    stmt = pg_insert(model).values(entries).on_conflict_do_nothing(
                        index_elements=on_conflict_target
                    )
                else:
                    stmt = pg_insert(model).values(entries).on_conflict_do_update(
                        index_elements=on_conflict_target,
                        set_=cols_to_update
                    )

                try:
                    await session.execute(stmt)
                    updated_record_counts[table_name] += len(entries)
                    print(
                        f"[DEBUG] Upserted into '{table_name}': {len(entries)} rows")
                except Exception as exc:
                    print(f"[ERROR] {table_name} bulk upsert failed: {exc}")
                    raise HTTPException(
                        status_code=500, detail=f"Database upsert failed for {table_name}: {exc}")

        await session.commit()

        return {
            "success": True,
            "message": "File data updated successfully",
            "updated_records": updated_record_counts,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        await session.rollback()  # Rollback on any error
        print(f"[ERROR] Full update transaction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update file data: {str(e)}"
        )

# routes/schedule_routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
# Added Any for the commented-out POST route
from typing import Optional, List, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update

# Import Base and get_async_session from your existing database.py
from database import Base, get_async_session

router = APIRouter(
    prefix="/schedules",
    tags=["Schedules"]
)

# --- Pydantic Schemas ---


class ScheduleBase(BaseModel):
    """Base schema for Schedule attributes."""
    period: str = Field(
        ..., description="The period of the schedule (e.g., '0:00:15' for 15 seconds).")
    starttime: Optional[str] = Field(
        None, description="Optional start time for the schedule (e.g., '2025-01-01T00:00:00Z').", alias="startTime")

    model_config = {
        "populate_by_name": True
    }

# Commented out ScheduleCreate model as create functionality is removed
# class ScheduleCreate(ScheduleBase):
#     """Schema for creating a new Schedule."""
#     id: str = Field(..., max_length=128, description="Unique identifier for the schedule.")

# Enabled ScheduleUpdate model for update functionality


class ScheduleUpdate(ScheduleBase):
    """Schema for updating an existing Schedule."""
    period: Optional[str] = Field(
        None, description="The period of the schedule (e.g., '0:00:15' for 15 seconds).")
    starttime: Optional[str] = Field(
        None, description="Optional start time for the schedule (e.g., '2025-01-01T00:00:00Z').", alias="startTime")


class ScheduleResponse(ScheduleBase):
    """Schema for responding with Schedule data, including DB-managed fields."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- API Endpoints ---

# Commented out the POST endpoint as create functionality is removed
@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    # Changed to Any to prevent Pydantic validation for a non-existent route
    schedule_data: Any,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Creates a new Schedule in the database.
    Raises a 400 error if a schedule with the given ID already exists.
    """
    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                        detail="Schedule creation is not allowed.")


@router.get("/", response_model=List[ScheduleResponse])
async def read_schedules(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Retrieves a list of all Schedules from the database.
    Supports pagination with 'skip' and 'limit' parameters.
    """
    ScheduleDB = Base.classes.eds_schedules
    result = await db.execute(select(ScheduleDB).offset(skip).limit(limit))
    schedules = result.scalars().all()
    return schedules


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def read_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Retrieves a single Schedule by its ID.
    Raises a 404 error if the schedule is not found.
    """
    ScheduleDB = Base.classes.eds_schedules
    result = await db.execute(
        select(ScheduleDB).where(ScheduleDB.id == schedule_id)
    )
    db_schedule = result.scalar_one_or_none()
    if db_schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return db_schedule

# PUT endpoint for update functionality remains enabled


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    schedule_update_data: ScheduleUpdate,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Updates an existing Schedule by its ID.
    Only provided fields in the request body will be updated.
    Raises a 404 error if the schedule is not found.
    """
    ScheduleDB = Base.classes.eds_schedules
    result = await db.execute(
        select(ScheduleDB).where(ScheduleDB.id == schedule_id)
    )
    db_schedule = result.scalar_one_or_none()

    if db_schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    update_data = schedule_update_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_schedule, key, value)

    await db.commit()
    await db.refresh(db_schedule)
    return db_schedule

# DELETE endpoint remains commented out
# @router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_schedule(
#     schedule_id: str,
#     db: AsyncSession = Depends(get_async_session)
# ):
#     """
#     Deletes a Schedule by its ID.
#     Raises a 404 error if the schedule is not found.
#     """
#     ScheduleDB = Base.classes.eds_schedules
#     result = await db.execute(
#         select(ScheduleDB).where(ScheduleDB.id == schedule_id)
#     )
#     db_schedule = result.scalar_one_or_none()

#     if db_schedule is None:
#         raise HTTPException(status_code=404, detail="Schedule not found")

#     await db.delete(db_schedule)
#     await db.commit()
#     return

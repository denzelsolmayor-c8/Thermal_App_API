# routes/data_selector_routes.py

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
    prefix="/data_selectors",
    tags=["Data Selectors"]
)

# --- Pydantic Schemas ---


class DataSelectorBase(BaseModel):
    """Base schema for Data Selector attributes."""
    streamfilter: Optional[str] = Field(None, max_length=256, alias="streamFilter",
                                        description="Filter string for data streams (e.g., 'Id:Modbus OR Id:Opc').")
    absolutedeadband: Optional[str] = Field(
        None, max_length=128, alias="absoluteDeadband", description="Absolute deadband value (e.g., '0.5').")
    percentchange: Optional[str] = Field(
        None, max_length=128, alias="percentChange", description="Percent change threshold (e.g., '10').")
    expirationperiod: Optional[str] = Field(None, max_length=128, alias="expirationPeriod",
                                            description="Period after which data expires (e.g., '0:01:00' for 1 minute).")

    model_config = {
        "populate_by_name": True
    }

# Commented out DataSelectorCreate model as create functionality is removed
# class DataSelectorCreate(DataSelectorBase):
#     """Schema for creating a new Data Selector."""
#     id: str = Field(..., max_length=128, description="Unique identifier for the data selector.")

# Enabled DataSelectorUpdate model for update functionality


class DataSelectorUpdate(DataSelectorBase):
    """Schema for updating an existing Data Selector."""
    streamfilter: Optional[str] = Field(
        None, max_length=256, alias="streamFilter")
    absolutedeadband: Optional[str] = Field(
        None, max_length=128, alias="absoluteDeadband")
    percentchange: Optional[str] = Field(
        None, max_length=128, alias="percentChange")
    expirationperiod: Optional[str] = Field(
        None, max_length=128, alias="expirationPeriod")


class DataSelectorResponse(DataSelectorBase):
    """Schema for responding with Data Selector data, including DB-managed fields."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- API Endpoints ---

# Commented out the POST endpoint as create functionality is removed
@router.post("/", response_model=DataSelectorResponse, status_code=status.HTTP_201_CREATED)
async def create_data_selector(
    # Changed to Any to prevent Pydantic validation for a non-existent route
    selector_data: Any,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Creates a new Data Selector in the database.
    Raises a 400 error if a selector with the given ID already exists.
    """
    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                        detail="Data Selector creation is not allowed.")


@router.get("/", response_model=List[DataSelectorResponse])
async def read_data_selectors(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Retrieves a list of all Data Selectors from the database.
    Supports pagination with 'skip' and 'limit' parameters.
    """
    DataSelectorDB = Base.classes.eds_data_selectors
    result = await db.execute(select(DataSelectorDB).offset(skip).limit(limit))
    selectors = result.scalars().all()
    return selectors


@router.get("/{selector_id}", response_model=DataSelectorResponse)
async def read_data_selector(
    selector_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Retrieves a single Data Selector by its ID.
    Raises a 404 error if the selector is not found.
    """
    DataSelectorDB = Base.classes.eds_data_selectors
    result = await db.execute(
        select(DataSelectorDB).where(DataSelectorDB.id == selector_id)
    )
    db_selector = result.scalar_one_or_none()
    if db_selector is None:
        raise HTTPException(status_code=404, detail="Data Selector not found")
    return db_selector

# PUT endpoint for update functionality remains enabled


@router.put("/{selector_id}", response_model=DataSelectorResponse)
async def update_data_selector(
    selector_id: str,
    selector_update_data: DataSelectorUpdate,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Updates an existing Data Selector by its ID.
    Only provided fields in the request body will be updated.
    Raises a 404 error if the selector is not found.
    """
    DataSelectorDB = Base.classes.eds_data_selectors
    result = await db.execute(
        select(DataSelectorDB).where(DataSelectorDB.id == selector_id)
    )
    db_selector = result.scalar_one_or_none()

    if db_selector is None:
        raise HTTPException(status_code=404, detail="Data Selector not found")

    update_data = selector_update_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_selector, key, value)

    await db.commit()
    await db.refresh(db_selector)
    return db_selector

# DELETE endpoint remains commented out
# @router.delete("/{selector_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_data_selector(
#     selector_id: str,
#     db: AsyncSession = Depends(get_async_session)
# ):
#     """
#     Deletes a Data Selector by its ID.
#     Raises a 404 error if the selector is not found.
#     """
#     DataSelectorDB = Base.classes.eds_data_selectors
#     result = await db.execute(
#         select(DataSelectorDB).where(DataSelectorDB.id == selector_id)
#     )
#     db_selector = result.scalar_one_or_none()

#     if db_selector is None:
#         raise HTTPException(status_code=404, detail="Data Selector not found")

#     await db.delete(db_selector)
#     await db.commit()
#     return

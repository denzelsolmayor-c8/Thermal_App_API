from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update

# Import Base and get_async_session from your existing database.py
from database import Base, get_async_session

router = APIRouter(
    prefix="/egress_endpoints",
    tags=["Egress Endpoints"]
)

# --- Pydantic Schemas ---


class EgressEndpointBase(BaseModel):
    """Base schema for Egress Endpoint attributes."""
    endpoint: HttpUrl = Field(...,
                              description="The URL of the egress endpoint.")
    username: Optional[str] = Field(None, max_length=128, alias="userName")
    password: Optional[str] = Field(None, max_length=128)
    clientid: Optional[str] = Field(None, max_length=128, alias="clientId")
    clientsecret: Optional[str] = Field(
        None, max_length=256, alias="clientSecret")
    debugexpiration: Optional[str] = Field(
        None, max_length=128, description="Debug expiration date/time string (e.g., '2025-12-31').", alias="debugExpiration")
    tokenendpoint: Optional[HttpUrl] = Field(
        None, description="The OAuth 2.0 token endpoint URL.", alias="tokenEndpoint")
    validateendpointcertificate: Optional[bool] = Field(
        True, alias="validateEndpointCertificate")

    model_config = {
        "populate_by_name": True
    }

# Commented out EgressEndpointCreate model as create functionality is removed
# class EgressEndpointCreate(EgressEndpointBase):
#     """Schema for creating a new Egress Endpoint."""
#     id: str = Field(..., max_length=128, description="Unique identifier for the egress endpoint.")

# Enabled EgressEndpointUpdate model for update functionality


class EgressEndpointUpdate(EgressEndpointBase):
    """Schema for updating an existing Egress Endpoint (all fields are optional)."""
    endpoint: Optional[HttpUrl] = Field(
        None, description="The URL of the egress endpoint.")
    tokenendpoint: Optional[HttpUrl] = Field(
        None, description="The OAuth 2.0 token endpoint URL.")


class EgressEndpointResponse(EgressEndpointBase):
    """Schema for responding with Egress Endpoint data, including DB-managed fields."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Helper Function for Type Conversion ---


def convert_httpurl_to_str(data: dict[str, Any]) -> dict[str, Any]:
    """
    Converts HttpUrl instances within a dictionary to their string representations.
    This is necessary because SQLAlchemy's automap does not automatically
    handle Pydantic's HttpUrl type for database insertion/update.
    """
    converted_data = {}
    for key, value in data.items():
        if isinstance(value, HttpUrl):
            converted_data[key] = str(value)
        else:
            converted_data[key] = value
    return converted_data

# --- API Endpoints ---

# Commented out the POST endpoint as create functionality is removed


class EgressEndpointCreate(EgressEndpointBase):
    id: str = Field(..., max_length=128, description="Unique identifier for the egress endpoint.")

@router.post("/", response_model=EgressEndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_egress_endpoint(
    endpoint_data: EgressEndpointCreate,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Creates a new Egress Endpoint in the database.
    Raises a 400 error if an endpoint with the given ID already exists.
    """
    EgressEndpointDB = Base.classes.eds_egress_endpoints

    # Ensure uniqueness
    existing = await db.execute(select(EgressEndpointDB).where(EgressEndpointDB.id == endpoint_data.id))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail=f"Egress Endpoint with ID '{endpoint_data.id}' already exists.")

    # Prepare data for DB (use internal field names, not aliases)
    create_dict = convert_httpurl_to_str(endpoint_data.model_dump(by_alias=False))
    db_obj = EgressEndpointDB(**create_dict)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


@router.get("/", response_model=List[EgressEndpointResponse])
async def read_egress_endpoints(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Retrieves a list of all Egress Endpoints from the database.
    Supports pagination with 'skip' and 'limit' parameters.
    """
    EgressEndpointDB = Base.classes.eds_egress_endpoints
    result = await db.execute(select(EgressEndpointDB).offset(skip).limit(limit))
    endpoints = result.scalars().all()
    return endpoints


@router.get("/{egress_endpoint_id}", response_model=EgressEndpointResponse)
async def read_egress_endpoint(
    egress_endpoint_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Retrieves a single Egress Endpoint by its ID.
    Raises a 404 error if the endpoint is not found.
    """
    EgressEndpointDB = Base.classes.eds_egress_endpoints
    result = await db.execute(
        select(EgressEndpointDB).where(
            EgressEndpointDB.id == egress_endpoint_id)
    )
    db_endpoint = result.scalar_one_or_none()
    if db_endpoint is None:
        raise HTTPException(
            status_code=404, detail="Egress Endpoint not found")
    return db_endpoint

# Enabled the PUT endpoint for update functionality


@router.put("/{egress_endpoint_id}", response_model=EgressEndpointResponse)
async def update_egress_endpoint(
    egress_endpoint_id: str,
    endpoint_update_data: EgressEndpointUpdate,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Updates an existing Egress Endpoint by its ID.
    Only provided fields in the request body will be updated.
    Raises a 404 error if the endpoint is not found.
    """
    EgressEndpointDB = Base.classes.eds_egress_endpoints
    result = await db.execute(
        select(EgressEndpointDB).where(
            EgressEndpointDB.id == egress_endpoint_id)
    )
    db_endpoint = result.scalar_one_or_none()

    if db_endpoint is None:
        raise HTTPException(
            status_code=404, detail="Egress Endpoint not found")

    update_data = convert_httpurl_to_str(
        endpoint_update_data.model_dump(exclude_unset=True))
    print(f"DEBUG: Converted data for update in PUT: {update_data}")

    for key, value in update_data.items():
        setattr(db_endpoint, key, value)

    await db.commit()
    await db.refresh(db_endpoint)
    return db_endpoint

# Commented out the DELETE endpoint as per request
# @router.delete("/{egress_endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_egress_endpoint(
#     egress_endpoint_id: str,
#     db: AsyncSession = Depends(get_async_session)
# ):
#     """
#     Deletes an Egress Endpoint by its ID.
#     Raises a 404 error if the endpoint is not found.
#     """
#     EgressEndpointDB = Base.classes.eds_egress_endpoints
#     result = await db.execute(
#         select(EgressEndpointDB).where(EgressEndpointDB.id == egress_endpoint_id)
#     )
#     db_endpoint = result.scalar_one_or_none()

#     if db_endpoint is None:
#         raise HTTPException(status_code=404, detail="Egress Endpoint not found")

#     await db.delete(db_endpoint)
#     await db.commit()
#     return

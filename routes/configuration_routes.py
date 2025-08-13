# routes/configuration_routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
# Ensure 'update' is imported if used elsewhere
from sqlalchemy import select, delete, update

# Import Base and get_async_session from your existing database.py
from database import Base, get_async_session

# Import response models from other routes for embedding
from routes.egress_endpoints_routes import EgressEndpointResponse
from routes.schedule_routes import ScheduleResponse
# Re-added DataSelectorResponse
from routes.data_selector_routes import DataSelectorResponse


router = APIRouter(
    prefix="/configurations",
    tags=["Configurations"]
)

# --- Pydantic Schemas ---


class ConfigurationBase(BaseModel):
    name: str = Field(..., max_length=128,
                      description="Display name for the configuration.")
    description: Optional[str] = Field(None, max_length=128)
    enabled: bool = Field(True)
    endpointId: Optional[str] = Field(None, max_length=128, alias="endpointid")
    scheduleId: Optional[str] = Field(None, max_length=128, alias="scheduleid")
    # dataSelectorId removed from base as it's part of mapping, not direct config table
    namespaceId: str = Field("default", max_length=128, alias="namespaceid")
    backfill: bool = Field(False)
    streamPrefix: Optional[str] = Field(
        None, max_length=128, alias="streamprefix")
    typePrefix: Optional[str] = Field(None, max_length=128, alias="typeprefix")
    model_config = ConfigDict(populate_by_name=True)


class ConfigurationCreate(ConfigurationBase):
    id: str = Field(..., max_length=128)

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        if 'name' not in data or data['name'] is None:
            data['name'] = data['id']
        return data


class ConfigurationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = Field(None, max_length=128)
    enabled: Optional[bool] = Field(None)
    endpointId: Optional[str] = Field(None, max_length=128, alias="endpointid")
    scheduleId: Optional[str] = Field(None, max_length=128, alias="scheduleid")
    # Re-added: Accept a list of Data Selector IDs for many-to-many
    dataSelectorIds: Optional[List[str]] = Field(None, alias="dataSelectorIds")
    namespaceId: Optional[str] = Field(
        None, max_length=128, alias="namespaceid")
    backfill: Optional[bool] = Field(None)
    streamPrefix: Optional[str] = Field(
        None, max_length=128, alias="streamprefix")
    typePrefix: Optional[str] = Field(None, max_length=128, alias="typeprefix")
    model_config = ConfigDict(populate_by_name=True)


class ConfigurationResponse(ConfigurationBase):
    id: str
    created_at: datetime
    updated_at: datetime
    endpoint: Optional[EgressEndpointResponse] = None
    schedule: Optional[ScheduleResponse] = None
    # Re-added: Respond with a list of full Data Selector objects for many-to-many
    dataSelectors: List[DataSelectorResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


# --- Helper function to hydrate a configuration object ---
# Changed return type
async def hydrate_configuration(db_config: Any, db: AsyncSession) -> ConfigurationResponse:
    EgressEndpointDB = Base.classes.eds_egress_endpoints
    ScheduleDB = Base.classes.eds_schedules
    DataSelectorDB = Base.classes.eds_data_selectors
    MappingDB = Base.classes.eds_egress_config_data_selectors_mapping  # Re-added MappingDB

    # Start with a Pydantic model instance for easier population
    config_response = ConfigurationResponse.model_validate(db_config)

    if config_response.endpointId:
        endpoint_result = await db.execute(select(EgressEndpointDB).where(EgressEndpointDB.id == config_response.endpointId))
        if db_endpoint := endpoint_result.scalar_one_or_none():
            config_response.endpoint = EgressEndpointResponse.model_validate(
                db_endpoint)

    if config_response.scheduleId:
        schedule_result = await db.execute(select(ScheduleDB).where(ScheduleDB.id == config_response.scheduleId))
        if db_schedule := schedule_result.scalar_one_or_none():
            config_response.schedule = ScheduleResponse.model_validate(
                db_schedule)

    # Re-added: Hydrate Data Selectors from the mapping table
    mapping_result = await db.execute(select(MappingDB.ds_id).where(MappingDB.ec_id == config_response.id))
    ds_ids = [row[0] for row in mapping_result.all()]

    config_response.dataSelectors = []  # Initialize as empty list
    if ds_ids:
        ds_result = await db.execute(select(DataSelectorDB).where(DataSelectorDB.id.in_(ds_ids)))
        db_data_selectors = ds_result.scalars().all()
        config_response.dataSelectors = [
            DataSelectorResponse.model_validate(ds) for ds in db_data_selectors]

    return config_response  # Return the Pydantic model instance

# --- API Endpoints ---


@router.post("/", response_model=ConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def create_configuration(config_data: ConfigurationCreate, db: AsyncSession = Depends(get_async_session)):
    ConfigurationDB = Base.classes.eds_egress_configurations
    if config_data.id != config_data.name:
        raise HTTPException(
            status_code=400, detail="Configuration ID must be the same as its Name.")
    if (await db.execute(select(ConfigurationDB).where(ConfigurationDB.id == config_data.id))).scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail=f"Configuration with ID '{config_data.id}' already exists.")

    db_config = ConfigurationDB(**config_data.model_dump(by_alias=True))
    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)

    # Hydrate after creation
    return await hydrate_configuration(db_config, db)


@router.get("/", response_model=List[ConfigurationResponse])
async def read_configurations(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_session)):
    ConfigurationDB = Base.classes.eds_egress_configurations
    result = await db.execute(select(ConfigurationDB).offset(skip).limit(limit))
    configurations_raw = result.scalars().all()
    hydrated_configs = [await hydrate_configuration(config, db) for config in configurations_raw]
    return hydrated_configs


@router.get("/{config_id}", response_model=ConfigurationResponse)
async def read_configuration(config_id: str, db: AsyncSession = Depends(get_async_session)):
    ConfigurationDB = Base.classes.eds_egress_configurations
    result = await db.execute(select(ConfigurationDB).where(ConfigurationDB.id == config_id))
    db_config = result.scalar_one_or_none()
    if db_config is None:
        raise HTTPException(status_code=404, detail="Configuration not found")

    return await hydrate_configuration(db_config, db)


@router.put("/{config_id}", response_model=ConfigurationResponse)
async def update_configuration(config_id: str, config_update_data: ConfigurationUpdate, db: AsyncSession = Depends(get_async_session)):
    ConfigurationDB = Base.classes.eds_egress_configurations
    MappingDB = Base.classes.eds_egress_config_data_selectors_mapping  # Re-added MappingDB

    async with db.begin():  # Use a transaction
        result = await db.execute(select(ConfigurationDB).where(ConfigurationDB.id == config_id))
        db_config = result.scalar_one_or_none()

        if db_config is None:
            raise HTTPException(
                status_code=404, detail="Configuration not found")

        update_data = config_update_data.model_dump(
            exclude_unset=True, by_alias=True)
        data_selector_ids = update_data.pop(
            "dataSelectorIds", None)  # Pop dataSelectorIds

        for key, value in update_data.items():
            setattr(db_config, key, value)

        # Re-added: Update the mapping table
        if data_selector_ids is not None:  # Only update if dataSelectorIds was provided in the payload
            # Delete existing mappings
            await db.execute(delete(MappingDB).where(MappingDB.ec_id == config_id))
            if data_selector_ids:  # If new IDs are provided, add them
                new_mappings = [MappingDB(ec_id=config_id, ds_id=ds_id)
                                for ds_id in data_selector_ids]
                db.add_all(new_mappings)

    # Re-fetch and hydrate the fully updated configuration
    refreshed_config = await db.get(ConfigurationDB, config_id)
    if not refreshed_config:
        # Should not happen
        raise HTTPException(
            status_code=404, detail="Configuration not found after update.")

    await db.refresh(refreshed_config)
    # Return hydrated config
    return await hydrate_configuration(refreshed_config, db)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration(config_id: str, db: AsyncSession = Depends(get_async_session)):
    """Delete configuration and its selector mappings."""
    ConfigurationDB = Base.classes.eds_egress_configurations
    MappingDB = Base.classes.eds_egress_config_data_selectors_mapping

    # Find configuration
    result = await db.execute(select(ConfigurationDB).where(ConfigurationDB.id == config_id))
    db_config = result.scalar_one_or_none()
    if db_config is None:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Remove selector mappings first
    await db.execute(delete(MappingDB).where(MappingDB.ec_id == config_id))

    # Delete configuration
    await db.delete(db_config)
    await db.commit()
    return

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, join, distinct

from database import Base, get_async_session
from routes.egress_endpoints_routes import EgressEndpointResponse
from routes.schedule_routes import ScheduleResponse
from routes.data_selector_routes import DataSelectorResponse

router = APIRouter(
    prefix="/combined_config_details",  # A descriptive prefix for the new endpoint
    tags=["Combined Configuration Data"]
)

# Pydantic model for the first object (joined configurations and ds_id)


class ConfigurationJoinedWithDsId(BaseModel):
    """
    Schema for the first object in the response array, representing
    eds_egress_configurations joined with ds_id from the mapping table.
    """
    id: str
    name: str
    description: Optional[str] = None
    enabled: bool
    endpointId: Optional[str] = Field(None, alias="endpointid")
    scheduleId: Optional[str] = Field(None, alias="scheduleid")
    namespaceId: str = Field(alias="namespaceid")
    backfill: bool
    streamPrefix: Optional[str] = Field(None, alias="streamprefix")
    typePrefix: Optional[str] = Field(None, alias="typeprefix")
    created_at: datetime
    updated_at: datetime
    ds_id: str  # The joined data selector ID from the mapping table

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# NEW: Pydantic model to wrap each object in the response array with a 'type' header


class WrappedResponseObject(BaseModel):
    """
    Wrapper schema for each object in the combined data response array.
    Includes a 'type' field to describe the content and a 'data' field
    holding the actual list of objects.
    """
    type: str = Field(...,
                      description="A descriptive type for the data contained.")
    data: List[Any] = Field(...,
                            description="The list of data objects for this type.")

    model_config = ConfigDict(from_attributes=True)


# New bundle format: one entry per configuration with its components
class ConfigBundle(BaseModel):
    egressconfig: Dict[str, Any]
    egress_endpoint: Optional[Dict[str, Any]] = None
    schedule: Optional[Dict[str, Any]] = None
    data_selectors: List[Dict[str, Any]] = []


# Helper to build bundles
async def _build_bundles(db: AsyncSession, enabled_only: bool) -> List[ConfigBundle]:
    ConfigurationDB = Base.classes.eds_egress_configurations
    MappingDB = Base.classes.eds_egress_config_data_selectors_mapping
    EgressEndpointDB = Base.classes.eds_egress_endpoints
    ScheduleDB = Base.classes.eds_schedules
    DataSelectorDB = Base.classes.eds_data_selectors

    bundles: List[ConfigBundle] = []

    cfg_query = select(ConfigurationDB)
    if enabled_only:
        cfg_query = cfg_query.where(ConfigurationDB.enabled == True)

    cfg_rows = (await db.execute(cfg_query)).scalars().all()

    for cfg in cfg_rows:
        cfg_dict = {k: v for k, v in cfg.__dict__.items() if not k.startswith("_sa_")}

        # Endpoint
        endpoint_obj = None
        if cfg.endpointid:
            ep = (await db.execute(select(EgressEndpointDB).where(EgressEndpointDB.id == cfg.endpointid))).scalar_one_or_none()
            if ep:
                endpoint_obj = EgressEndpointResponse.model_validate(ep).model_dump()

        # Schedule
        schedule_obj = None
        if cfg.scheduleid:
            sch = (await db.execute(select(ScheduleDB).where(ScheduleDB.id == cfg.scheduleid))).scalar_one_or_none()
            if sch:
                schedule_obj = ScheduleResponse.model_validate(sch).model_dump()

        # Data selectors
        ds_list: List[Dict[str, Any]] = []
        ds_ids = [row[0] for row in (await db.execute(select(MappingDB.ds_id).where(MappingDB.ec_id == cfg.id))).all()]
        if ds_ids:
            for ds in (await db.execute(select(DataSelectorDB).where(DataSelectorDB.id.in_(ds_ids)))).scalars().all():
                ds_list.append(DataSelectorResponse.model_validate(ds).model_dump())

        bundles.append(ConfigBundle(
            egressconfig=cfg_dict,
            egress_endpoint=endpoint_obj,
            schedule=schedule_obj,
            data_selectors=ds_list,
        ))

    return bundles


@router.get("/", response_model=List[ConfigBundle], status_code=status.HTTP_200_OK)
async def get_configuration_bundles(db: AsyncSession = Depends(get_async_session)):
    try:
        return await _build_bundles(db, enabled_only=False)
    except Exception as e:
        print(f"ERROR in get_configuration_bundles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# New route: Same format but filtered to enabled configurations only
@router.get("/enabled", response_model=List[ConfigBundle], status_code=status.HTTP_200_OK)
async def get_enabled_configuration_bundles(db: AsyncSession = Depends(get_async_session)):
    try:
        return await _build_bundles(db, enabled_only=True)
    except Exception as e:
        print(f"ERROR in get_enabled_configuration_bundles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

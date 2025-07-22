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


@router.get("/", response_model=List[WrappedResponseObject], status_code=status.HTTP_200_OK)
async def get_all_related_config_data(db: AsyncSession = Depends(get_async_session)):
    """
    Retrieves a JSON payload containing an array of 4 objects, each with a 'type' header:
    1. 'egress_configurations': All data from eds_egress_configurations joined with ds_id from
       eds_egress_config_data_selectors_mapping.
    2. 'egress_endpoints': All unique eds_egress_endpoints referenced by eds_egress_configurations.
    3. 'schedules': All unique eds_schedules referenced by eds_egress_configurations.
    4. 'data_selectors': All unique eds_data_selectors referenced by ds_id in
       eds_egress_config_data_selectors_mapping.
    """
    ConfigurationDB = Base.classes.eds_egress_configurations
    MappingDB = Base.classes.eds_egress_config_data_selectors_mapping
    EgressEndpointDB = Base.classes.eds_egress_endpoints
    ScheduleDB = Base.classes.eds_schedules
    DataSelectorDB = Base.classes.eds_data_selectors

    response_array = []

    try:
        # --- 1st Object: Joined Configurations and ds_id ---
        stmt_joined_configs = select(ConfigurationDB, MappingDB.ds_id).join(
            MappingDB, ConfigurationDB.id == MappingDB.ec_id
        )
        joined_result = await db.execute(stmt_joined_configs)

        joined_configs_list = []
        for config_obj, ds_id_val in joined_result.all():
            config_dict = {
                k: v for k, v in config_obj.__dict__.items() if not k.startswith('_sa_')}
            config_dict['ds_id'] = ds_id_val
            joined_configs_list.append(
                ConfigurationJoinedWithDsId.model_validate(config_dict))

        # Wrap the data with a type header
        response_array.append(WrappedResponseObject(
            type="egress_configurations", data=joined_configs_list))

        # --- Collect unique IDs for subsequent queries ---
        # Fetch all configurations to get unique endpointId and scheduleId
        all_configs_result = await db.execute(select(ConfigurationDB.endpointid, ConfigurationDB.scheduleid))
        unique_endpoint_ids = set()
        unique_schedule_ids = set()
        for endpoint_id, schedule_id in all_configs_result.all():
            if endpoint_id:
                unique_endpoint_ids.add(endpoint_id)
            if schedule_id:
                unique_schedule_ids.add(schedule_id)

        # Fetch all unique ds_id's from the mapping table
        all_mapping_ds_ids_result = await db.execute(select(distinct(MappingDB.ds_id)))
        unique_data_selector_ids = {row[0]
                                    for row in all_mapping_ds_ids_result.all()}

        # --- 2nd Object: Contents of eds_egress_endpoints referenced by configurations ---
        referenced_endpoints = []
        if unique_endpoint_ids:
            endpoints_result = await db.execute(
                select(EgressEndpointDB).where(
                    EgressEndpointDB.id.in_(list(unique_endpoint_ids)))
            )
            referenced_endpoints = [EgressEndpointResponse.model_validate(
                ep) for ep in endpoints_result.scalars().all()]
        # Wrap the data with a type header
        response_array.append(WrappedResponseObject(
            type="egress_endpoints", data=referenced_endpoints))

        # --- 3rd Object: Contents of eds_schedules referenced by configurations ---
        referenced_schedules = []
        if unique_schedule_ids:
            schedules_result = await db.execute(
                select(ScheduleDB).where(
                    ScheduleDB.id.in_(list(unique_schedule_ids)))
            )
            referenced_schedules = [ScheduleResponse.model_validate(
                sch) for sch in schedules_result.scalars().all()]
        # Wrap the data with a type header
        response_array.append(WrappedResponseObject(
            type="schedules", data=referenced_schedules))

        # --- 4th Object: Contents of data selectors referenced by the mapping table ---
        referenced_data_selectors = []
        if unique_data_selector_ids:
            data_selectors_result = await db.execute(
                select(DataSelectorDB).where(
                    DataSelectorDB.id.in_(list(unique_data_selector_ids)))
            )
            referenced_data_selectors = [DataSelectorResponse.model_validate(
                ds) for ds in data_selectors_result.scalars().all()]
        # Wrap the data with a type header
        response_array.append(WrappedResponseObject(
            type="data_selectors", data=referenced_data_selectors))

        return response_array

    except Exception as e:
        # Log the full exception for debugging
        print(f"ERROR in get_all_related_config_data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve combined data: {e}"
        )

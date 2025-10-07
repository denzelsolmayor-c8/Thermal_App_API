# Thermal App API Documentation

This document provides comprehensive documentation for all endpoints in the Thermal App FastAPI application.

## Base URL

The API is typically served at `http://localhost:8000` (or your configured host/port).

## Authentication

Some endpoints require authentication. The application uses a simple token-based system with user management.

---

## Core Application Endpoints

### 1. Root Endpoint

**GET** `/`

**Description:** Basic health check endpoint.

**Response:**

```json
{
  "Hello": "World"
}
```

### 2. Camera Data

**GET** `/camera-data`

**Description:** Retrieves thermal camera data from Node-RED service.

**Response:**

```json
{
  // Thermal data from Node-RED service
  // Structure depends on the external service
}
```

**Error Responses:**

- `500` - Node-RED service error

### 3. Dynamic Table Data

**GET** `/data/{table_name}`

**Description:** Reads any table by name from the database.

**Parameters:**

- `table_name` (path): Name of the database table

**Response:**

```json
[
  {
    // Table data as key-value pairs
    // Structure depends on the table schema
  }
]
```

**Error Responses:**

- `400` - Table not found in database

---

## Data Management Endpoints

### 4. Upload File Data

**POST** `/api/upload-file-data`

**Description:** Uploads file data from a payload into various database tables. Handles dependencies between tables.

**Request Body:**

```json
{
  "id": "string",
  "filename": "string",
  "sheets": [
    {
      "sheet_name": "string",
      "headers": ["string"],
      "data": [["any"]],
      "created_at": "string"
    }
  ]
}
```

**Response:**

```json
{
  "message": "Upload complete",
  "record_count": {
    "mlc_zones": 0,
    "mlc_customer": 0,
    "mlc_camera_configs": 0,
    "mlc_camera_presets": 0,
    "mlc_temperatures": 0
  }
}
```

**Error Responses:**

- `500` - Database insert failed

### 5. Get Fixed Data

**GET** `/api/data/fixed`

**Description:** Retrieves fixed thermal data with all related information.

**Response:**

```json
{
  "sheets": [
    {
      "sheet_name": "string",
      "headers": [
        "camera_id",
        "camera_ip",
        "camera_name",
        "camera_location",
        "camera_type",
        "brand",
        "model",
        "firmware_version",
        "zone_id",
        "zone_name",
        "preset_number",
        "temperature_id",
        "measurement",
        "measurement_type",
        "description",
        "point_in_preset",
        "client_id",
        "client_name"
      ],
      "data": [["any"]],
      "created_at": "string"
    }
  ]
}
```

### 6. Get Dynamic Data

**GET** `/api/data`

**Description:** Retrieves thermal data with optional filtering.

**Query Parameters:**

- `camera_ip` (optional): Filter by camera IP address
- `preset_number` (optional): Filter by preset number

**Response:**

```json
{
  "sheets": [
    {
      "sheet_name": "string",
      "headers": [
        "camera_id",
        "camera_ip",
        "camera_name",
        "camera_location",
        "camera_type",
        "brand",
        "model",
        "firmware_version",
        "zone_id",
        "zone_name",
        "preset_number",
        "temperature_id",
        "measurement",
        "measurement_type",
        "description",
        "point_in_preset",
        "client_id",
        "client_name"
      ],
      "data": [["any"]],
      "created_at": "string"
    }
  ]
}
```

### 7. Update File Data

**PUT** `/api/data/update`

**Description:** Updates file data in the database. Performs upserts into respective database tables.

**Request Body:**

```json
{
  "sheets": [
    {
      "sheet_name": "string",
      "headers": ["string"],
      "data": [["any"]],
      "updated_at": "string"
    }
  ]
}
```

**Response:**

```json
{
  "success": true,
  "message": "File data updated successfully",
  "updated_records": {
    "customer": 0,
    "zones": 0,
    "camera_configs": 0,
    "camera_presets": 0,
    "camera_in_zone": 0,
    "temperatures": 0
  },
  "timestamp": "2025-01-01T00:00:00.000Z"
}
```

**Error Responses:**

- `500` - Failed to update file data

---

## Egress Endpoints Management

### 8. Create Egress Endpoint

**POST** `/egress_endpoints/`

**Description:** Creates a new Egress Endpoint in the database.

**Request Body:**

```json
{
  "id": "string",
  "endpoint": "https://example.com",
  "userName": "string",
  "password": "string",
  "clientId": "string",
  "clientSecret": "string",
  "debugExpiration": "2025-12-31",
  "tokenEndpoint": "https://example.com/token",
  "validateEndpointCertificate": true
}
```

**Response:**

```json
{
  "id": "string",
  "endpoint": "https://example.com",
  "userName": "string",
  "password": "string",
  "clientId": "string",
  "clientSecret": "string",
  "debugExpiration": "2025-12-31",
  "tokenEndpoint": "https://example.com/token",
  "validateEndpointCertificate": true,
  "created_at": "2025-01-01T00:00:00.000Z",
  "updated_at": "2025-01-01T00:00:00.000Z"
}
```

**Error Responses:**

- `400` - Egress Endpoint with ID already exists

### 9. Get All Egress Endpoints

**GET** `/egress_endpoints/`

**Description:** Retrieves a list of all Egress Endpoints with pagination.

**Query Parameters:**

- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum number of records to return (default: 100)

**Response:**

```json
[
  {
    "id": "string",
    "endpoint": "https://example.com",
    "userName": "string",
    "password": "string",
    "clientId": "string",
    "clientSecret": "string",
    "debugExpiration": "2025-12-31",
    "tokenEndpoint": "https://example.com/token",
    "validateEndpointCertificate": true,
    "created_at": "2025-01-01T00:00:00.000Z",
    "updated_at": "2025-01-01T00:00:00.000Z"
  }
]
```

### 10. Get Egress Endpoint by ID

**GET** `/egress_endpoints/{egress_endpoint_id}`

**Description:** Retrieves a single Egress Endpoint by its ID.

**Parameters:**

- `egress_endpoint_id` (path): The ID of the egress endpoint

**Response:**

```json
{
  "id": "string",
  "endpoint": "https://example.com",
  "userName": "string",
  "password": "string",
  "clientId": "string",
  "clientSecret": "string",
  "debugExpiration": "2025-12-31",
  "tokenEndpoint": "https://example.com/token",
  "validateEndpointCertificate": true,
  "created_at": "2025-01-01T00:00:00.000Z",
  "updated_at": "2025-01-01T00:00:00.000Z"
}
```

**Error Responses:**

- `404` - Egress Endpoint not found

### 11. Update Egress Endpoint

**PUT** `/egress_endpoints/{egress_endpoint_id}`

**Description:** Updates an existing Egress Endpoint by its ID.

**Parameters:**

- `egress_endpoint_id` (path): The ID of the egress endpoint

**Request Body:**

```json
{
  "endpoint": "https://example.com",
  "userName": "string",
  "password": "string",
  "clientId": "string",
  "clientSecret": "string",
  "debugExpiration": "2025-12-31",
  "tokenEndpoint": "https://example.com/token",
  "validateEndpointCertificate": true
}
```

**Response:**

```json
{
  "id": "string",
  "endpoint": "https://example.com",
  "userName": "string",
  "password": "string",
  "clientId": "string",
  "clientSecret": "string",
  "debugExpiration": "2025-12-31",
  "tokenEndpoint": "https://example.com/token",
  "validateEndpointCertificate": true,
  "created_at": "2025-01-01T00:00:00.000Z",
  "updated_at": "2025-01-01T00:00:00.000Z"
}
```

**Error Responses:**

- `404` - Egress Endpoint not found

### 12. Delete Egress Endpoint

**DELETE** `/egress_endpoints/{egress_endpoint_id}`

**Description:** Deletes an Egress Endpoint if not referenced by any configuration.

**Parameters:**

- `egress_endpoint_id` (path): The ID of the egress endpoint

**Response:**

- `204` - No Content (successful deletion)

**Error Responses:**

- `400` - Cannot delete endpoint: it is referenced by one or more configurations
- `404` - Egress Endpoint not found

---

## Schedule Management

### 13. Create Schedule

**POST** `/schedules/`

**Description:** Creates a new Schedule in the database.

**Request Body:**

```json
{
  "id": "string",
  "period": "0:00:15",
  "startTime": "2025-01-01T00:00:00Z"
}
```

**Response:**

```json
{
  "id": "string",
  "period": "0:00:15",
  "startTime": "2025-01-01T00:00:00Z",
  "created_at": "2025-01-01T00:00:00.000Z",
  "updated_at": "2025-01-01T00:00:00.000Z"
}
```

**Error Responses:**

- `400` - Schedule with ID already exists

### 14. Get All Schedules

**GET** `/schedules/`

**Description:** Retrieves a list of all Schedules with pagination.

**Query Parameters:**

- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum number of records to return (default: 100)

**Response:**

```json
[
  {
    "id": "string",
    "period": "0:00:15",
    "startTime": "2025-01-01T00:00:00Z",
    "created_at": "2025-01-01T00:00:00.000Z",
    "updated_at": "2025-01-01T00:00:00.000Z"
  }
]
```

### 15. Get Schedule by ID

**GET** `/schedules/{schedule_id}`

**Description:** Retrieves a single Schedule by its ID.

**Parameters:**

- `schedule_id` (path): The ID of the schedule

**Response:**

```json
{
  "id": "string",
  "period": "0:00:15",
  "startTime": "2025-01-01T00:00:00Z",
  "created_at": "2025-01-01T00:00:00.000Z",
  "updated_at": "2025-01-01T00:00:00.000Z"
}
```

**Error Responses:**

- `404` - Schedule not found

### 16. Update Schedule

**PUT** `/schedules/{schedule_id}`

**Description:** Updates an existing Schedule by its ID.

**Parameters:**

- `schedule_id` (path): The ID of the schedule

**Request Body:**

```json
{
  "period": "0:00:15",
  "startTime": "2025-01-01T00:00:00Z"
}
```

**Response:**

```json
{
  "id": "string",
  "period": "0:00:15",
  "startTime": "2025-01-01T00:00:00Z",
  "created_at": "2025-01-01T00:00:00.000Z",
  "updated_at": "2025-01-01T00:00:00.000Z"
}
```

**Error Responses:**

- `404` - Schedule not found

### 17. Delete Schedule

**DELETE** `/schedules/{schedule_id}`

**Description:** Deletes a Schedule if not referenced by any configuration.

**Parameters:**

- `schedule_id` (path): The ID of the schedule

**Response:**

- `204` - No Content (successful deletion)

**Error Responses:**

- `400` - Cannot delete schedule: it is referenced by one or more configurations
- `404` - Schedule not found

---

## Data Selector Management

### 18. Create Data Selector

**POST** `/data_selectors/`

**Description:** Creates a new Data Selector in the database.

**Request Body:**

```json
{
  "id": "string",
  "streamFilter": "Id:Modbus OR Id:Opc",
  "absoluteDeadband": "0.5",
  "percentChange": "10",
  "expirationPeriod": "0:01:00"
}
```

**Response:**

```json
{
  "id": "string",
  "streamFilter": "Id:Modbus OR Id:Opc",
  "absoluteDeadband": "0.5",
  "percentChange": "10",
  "expirationPeriod": "0:01:00",
  "created_at": "2025-01-01T00:00:00.000Z",
  "updated_at": "2025-01-01T00:00:00.000Z"
}
```

**Error Responses:**

- `400` - Data Selector with ID already exists

### 19. Get All Data Selectors

**GET** `/data_selectors/`

**Description:** Retrieves a list of all Data Selectors with pagination.

**Query Parameters:**

- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum number of records to return (default: 100)

**Response:**

```json
[
  {
    "id": "string",
    "streamFilter": "Id:Modbus OR Id:Opc",
    "absoluteDeadband": "0.5",
    "percentChange": "10",
    "expirationPeriod": "0:01:00",
    "created_at": "2025-01-01T00:00:00.000Z",
    "updated_at": "2025-01-01T00:00:00.000Z"
  }
]
```

### 20. Get Data Selector by ID

**GET** `/data_selectors/{selector_id}`

**Description:** Retrieves a single Data Selector by its ID.

**Parameters:**

- `selector_id` (path): The ID of the data selector

**Response:**

```json
{
  "id": "string",
  "streamFilter": "Id:Modbus OR Id:Opc",
  "absoluteDeadband": "0.5",
  "percentChange": "10",
  "expirationPeriod": "0:01:00",
  "created_at": "2025-01-01T00:00:00.000Z",
  "updated_at": "2025-01-01T00:00:00.000Z"
}
```

**Error Responses:**

- `404` - Data Selector not found

### 21. Update Data Selector

**PUT** `/data_selectors/{selector_id}`

**Description:** Updates an existing Data Selector by its ID.

**Parameters:**

- `selector_id` (path): The ID of the data selector

**Request Body:**

```json
{
  "streamFilter": "Id:Modbus OR Id:Opc",
  "absoluteDeadband": "0.5",
  "percentChange": "10",
  "expirationPeriod": "0:01:00"
}
```

**Response:**

```json
{
  "id": "string",
  "streamFilter": "Id:Modbus OR Id:Opc",
  "absoluteDeadband": "0.5",
  "percentChange": "10",
  "expirationPeriod": "0:01:00",
  "created_at": "2025-01-01T00:00:00.000Z",
  "updated_at": "2025-01-01T00:00:00.000Z"
}
```

**Error Responses:**

- `404` - Data Selector not found

### 22. Delete Data Selector

**DELETE** `/data_selectors/{selector_id}`

**Description:** Deletes a Data Selector if not referenced by any configuration mapping.

**Parameters:**

- `selector_id` (path): The ID of the data selector

**Response:**

- `204` - No Content (successful deletion)

**Error Responses:**

- `400` - Cannot delete data selector: it is referenced by one or more configurations
- `404` - Data Selector not found

---

## Configuration Management

### 23. Create Configuration

**POST** `/configurations/`

**Description:** Creates a new Configuration in the database.

**Request Body:**

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "enabled": true,
  "endpointid": "string",
  "scheduleid": "string",
  "namespaceid": "default",
  "backfill": false,
  "streamprefix": "string",
  "typeprefix": "string"
}
```

**Response:**

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "enabled": true,
  "endpointid": "string",
  "scheduleid": "string",
  "namespaceid": "default",
  "backfill": false,
  "streamprefix": "string",
  "typeprefix": "string",
  "created_at": "2025-01-01T00:00:00.000Z",
  "updated_at": "2025-01-01T00:00:00.000Z",
  "endpoint": {
    "id": "string",
    "endpoint": "https://example.com",
    "userName": "string",
    "password": "string",
    "clientId": "string",
    "clientSecret": "string",
    "debugExpiration": "2025-12-31",
    "tokenEndpoint": "https://example.com/token",
    "validateEndpointCertificate": true,
    "created_at": "2025-01-01T00:00:00.000Z",
    "updated_at": "2025-01-01T00:00:00.000Z"
  },
  "schedule": {
    "id": "string",
    "period": "0:00:15",
    "startTime": "2025-01-01T00:00:00Z",
    "created_at": "2025-01-01T00:00:00.000Z",
    "updated_at": "2025-01-01T00:00:00.000Z"
  },
  "dataSelectors": [
    {
      "id": "string",
      "streamFilter": "Id:Modbus OR Id:Opc",
      "absoluteDeadband": "0.5",
      "percentChange": "10",
      "expirationPeriod": "0:01:00",
      "created_at": "2025-01-01T00:00:00.000Z",
      "updated_at": "2025-01-01T00:00:00.000Z"
    }
  ]
}
```

**Error Responses:**

- `400` - Configuration ID must be the same as its Name
- `400` - Configuration with ID already exists

### 24. Get All Configurations

**GET** `/configurations/`

**Description:** Retrieves a list of all Configurations with pagination.

**Query Parameters:**

- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum number of records to return (default: 100)

**Response:**

```json
[
  {
    "id": "string",
    "name": "string",
    "description": "string",
    "enabled": true,
    "endpointid": "string",
    "scheduleid": "string",
    "namespaceid": "default",
    "backfill": false,
    "streamprefix": "string",
    "typeprefix": "string",
    "created_at": "2025-01-01T00:00:00.000Z",
    "updated_at": "2025-01-01T00:00:00.000Z",
    "endpoint": {
      // EgressEndpointResponse object or null
    },
    "schedule": {
      // ScheduleResponse object or null
    },
    "dataSelectors": [
      // Array of DataSelectorResponse objects
    ]
  }
]
```

### 25. Get Configuration by ID

**GET** `/configurations/{config_id}`

**Description:** Retrieves a single Configuration by its ID.

**Parameters:**

- `config_id` (path): The ID of the configuration

**Response:**

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "enabled": true,
  "endpointid": "string",
  "scheduleid": "string",
  "namespaceid": "default",
  "backfill": false,
  "streamprefix": "string",
  "typeprefix": "string",
  "created_at": "2025-01-01T00:00:00.000Z",
  "updated_at": "2025-01-01T00:00:00.000Z",
  "endpoint": {
    // EgressEndpointResponse object or null
  },
  "schedule": {
    // ScheduleResponse object or null
  },
  "dataSelectors": [
    // Array of DataSelectorResponse objects
  ]
}
```

**Error Responses:**

- `404` - Configuration not found

### 26. Update Configuration

**PUT** `/configurations/{config_id}`

**Description:** Updates an existing Configuration by its ID.

**Parameters:**

- `config_id` (path): The ID of the configuration

**Request Body:**

```json
{
  "name": "string",
  "description": "string",
  "enabled": true,
  "endpointid": "string",
  "scheduleid": "string",
  "dataSelectorIds": ["string"],
  "namespaceid": "default",
  "backfill": false,
  "streamprefix": "string",
  "typeprefix": "string"
}
```

**Response:**

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "enabled": true,
  "endpointid": "string",
  "scheduleid": "string",
  "namespaceid": "default",
  "backfill": false,
  "streamprefix": "string",
  "typeprefix": "string",
  "created_at": "2025-01-01T00:00:00.000Z",
  "updated_at": "2025-01-01T00:00:00.000Z",
  "endpoint": {
    // EgressEndpointResponse object or null
  },
  "schedule": {
    // ScheduleResponse object or null
  },
  "dataSelectors": [
    // Array of DataSelectorResponse objects
  ]
}
```

**Error Responses:**

- `404` - Configuration not found

### 27. Delete Configuration

**DELETE** `/configurations/{config_id}`

**Description:** Deletes a configuration and its selector mappings.

**Parameters:**

- `config_id` (path): The ID of the configuration

**Response:**

- `204` - No Content (successful deletion)

**Error Responses:**

- `404` - Configuration not found

---

## Combined Configuration Data

### 28. Get All Configuration Bundles

**GET** `/combined_config_details/`

**Description:** Retrieves all configuration bundles with their related components.

**Response:**

```json
[
  {
    "egressconfig": {
      "id": "string",
      "name": "string",
      "description": "string",
      "enabled": true,
      "endpointid": "string",
      "scheduleid": "string",
      "namespaceid": "default",
      "backfill": false,
      "streamprefix": "string",
      "typeprefix": "string",
      "created_at": "2025-01-01T00:00:00.000Z",
      "updated_at": "2025-01-01T00:00:00.000Z"
    },
    "egress_endpoint": {
      "id": "string",
      "endpoint": "https://example.com",
      "userName": "string",
      "password": "string",
      "clientId": "string",
      "clientSecret": "string",
      "debugExpiration": "2025-12-31",
      "tokenEndpoint": "https://example.com/token",
      "validateEndpointCertificate": true,
      "created_at": "2025-01-01T00:00:00.000Z",
      "updated_at": "2025-01-01T00:00:00.000Z"
    },
    "schedule": {
      "id": "string",
      "period": "0:00:15",
      "startTime": "2025-01-01T00:00:00Z",
      "created_at": "2025-01-01T00:00:00.000Z",
      "updated_at": "2025-01-01T00:00:00.000Z"
    },
    "data_selectors": [
      {
        "id": "string",
        "streamFilter": "Id:Modbus OR Id:Opc",
        "absoluteDeadband": "0.5",
        "percentChange": "10",
        "expirationPeriod": "0:01:00",
        "created_at": "2025-01-01T00:00:00.000Z",
        "updated_at": "2025-01-01T00:00:00.000Z"
      }
    ]
  }
]
```

### 29. Get Enabled Configuration Bundles

**GET** `/combined_config_details/enabled`

**Description:** Retrieves only enabled configuration bundles with their related components.

**Response:**

```json
[
  {
    "egressconfig": {
      // Configuration object (enabled only)
    },
    "egress_endpoint": {
      // EgressEndpointResponse object or null
    },
    "schedule": {
      // ScheduleResponse object or null
    },
    "data_selectors": [
      // Array of DataSelectorResponse objects
    ]
  }
]
```

---

## User Management

### 30. User Login

**POST** `/auth/login`

**Description:** Authenticates a user and returns a token.

**Request Body:**

```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**

```json
{
  "access_token": "token",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "string",
    "role_id": 1,
    "role": "string"
  },
  "must_change_password": false
}
```

**Error Responses:**

- `401` - Invalid credentials

### 31. Change Password

**POST** `/auth/change-password`

**Description:** Changes a user's password.

**Request Body:**

```json
{
  "username": "string",
  "current_password": "string",
  "new_password": "string"
}
```

**Response:**

```json
{
  "status": "ok"
}
```

**Error Responses:**

- `400` - Current password is incorrect
- `400` - Password is too common
- `400` - Password must not contain username
- `404` - User not found

### 32. List Users

**GET** `/users`

**Description:** Retrieves a list of all users.

**Response:**

```json
[
  {
    "id": 1,
    "username": "string",
    "role_id": 1,
    "role": "string",
    "created_at": "2025-01-01T00:00:00.000Z",
    "updated_at": "2025-01-01T00:00:00.000Z"
  }
]
```

### 33. Create User

**POST** `/users`

**Description:** Creates a new user.

**Request Body:**

```json
{
  "username": "string",
  "role_id": 1,
  "role_name": "string",
  "default_password": "string"
}
```

**Response:**

```json
{
  "status": "ok"
}
```

**Error Responses:**

- `400` - username is required
- `400` - role_name not found

### 34. Update User

**PATCH** `/users/{user_id}`

**Description:** Updates a user's role.

**Parameters:**

- `user_id` (path): The ID of the user

**Request Body:**

```json
{
  "role_id": 1,
  "role_name": "string"
}
```

**Response:**

```json
{
  "status": "ok"
}
```

**Error Responses:**

- `400` - role_name not found
- `400` - Nothing to update

### 35. Delete User

**DELETE** `/users/{user_id}`

**Description:** Deletes a user.

**Parameters:**

- `user_id` (path): The ID of the user

**Response:**

```json
{
  "status": "ok"
}
```

### 36. List Roles

**GET** `/roles`

**Description:** Retrieves a list of all roles.

**Response:**

```json
[
  {
    "id": 1,
    "role_name": "string",
    "description": "string"
  }
]
```

### 37. Get Role Privileges

**GET** `/roles/{role_id}/privileges`

**Description:** Retrieves privileges for a specific role.

**Parameters:**

- `role_id` (path): The ID of the role

**Response:**

```json
[
  {
    "id": 1,
    "privilege_name": "string",
    "description": "string"
  }
]
```

---

## Error Handling

All endpoints may return the following HTTP status codes:

- `200` - OK (successful request)
- `201` - Created (successful creation)
- `204` - No Content (successful deletion)
- `400` - Bad Request (invalid request data)
- `401` - Unauthorized (authentication required)
- `404` - Not Found (resource not found)
- `500` - Internal Server Error (server error)

## Common Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

## Notes

1. **Database Connection**: The application uses PostgreSQL with async SQLAlchemy
2. **CORS**: The application has CORS middleware enabled for all origins
3. **Authentication**: Simple token-based authentication system
4. **Data Validation**: All endpoints use Pydantic models for request/response validation
5. **Pagination**: List endpoints support `skip` and `limit` parameters for pagination
6. **Relationships**: Many endpoints return related data (e.g., configurations include their endpoints, schedules, and data selectors)

## Database Tables

The application works with the following main database tables:

- `mlc_camera_configs` - Camera configuration data
- `mlc_camera_presets` - Camera preset configurations
- `mlc_zones` - Zone definitions
- `mlc_customer` - Customer information
- `mlc_temperatures` - Temperature measurement data
- `eds_egress_endpoints` - Egress endpoint configurations
- `eds_schedules` - Schedule configurations
- `eds_data_selectors` - Data selector configurations
- `eds_egress_configurations` - Main configuration table
- `usm_user_accounts` - User account information
- `usm_roles` - User roles
- `usm_privileges` - System privileges

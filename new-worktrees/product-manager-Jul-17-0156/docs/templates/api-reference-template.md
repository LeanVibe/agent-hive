# [API Name] Reference

**Status**: ✅ Implemented / ❌ Planned / 🔄 In Progress  
**Version**: X.Y.Z  
**Last Updated**: Date  

## Overview
Brief description of the API's purpose and scope.

## Authentication
Authentication requirements and examples.

## Base URL
```
https://api.example.com/v1
```

## Endpoints

### GET /endpoint
**Description**: What this endpoint does.

**Parameters**:
- `param1` (string, required): Description
- `param2` (integer, optional): Description

**Request Example**:
```bash
curl -X GET "https://api.example.com/v1/endpoint?param1=value" \
  -H "Authorization: Bearer token"
```

**Response Example**:
```json
{
  "status": "success",
  "data": {
    "key": "value"
  }
}
```

**Error Responses**:
- `400`: Bad Request - Invalid parameters
- `401`: Unauthorized - Missing or invalid token
- `404`: Not Found - Resource not found

## Rate Limiting
Rate limiting information and headers.

## Error Handling
Standard error response format and common errors.

## Examples
Real-world usage examples with complete workflows.
# API Conventions

## Versioning

All application endpoints are under `/api/v1/`. Compatibility aliases for the
existing simulation frontend are documented when added.

## Content type

Requests and responses use JSON. The API accepts camelCase input and returns
camelCase output while Python internals remain snake_case.

## Authentication

- Access token lifetime: 15 minutes.
- Refresh token lifetime: 30 days.
- Refresh rotation and blacklist are enabled.
- Send the access token as `Authorization: Bearer <token>`.
- Refresh with `POST /api/v1/auth/refresh/` and body `{"refresh": "..."}`.
- Logout blacklists the supplied refresh token.

## Response envelopes

Single resources:

```json
{
  "data": {
    "id": "...",
    "createdAt": "..."
  }
}
```

Lists:

```json
{
  "data": [],
  "meta": {
    "count": 0,
    "next": null,
    "previous": null,
    "page": 1,
    "pageSize": 50
  }
}
```

Errors:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Enter a valid email address.",
    "details": {
      "email": ["Enter a valid email address."]
    },
    "requestId": "..."
  }
}
```

Every response includes `X-Request-ID`.

## Pagination and filtering

- Page size query parameter: `pageSize` (camelCase input is normalised).
- Default page size: 50.
- Maximum page size: 200.
- List endpoints may expose `search`, `ordering` and filter query parameters.

## Idempotency

Offline-capable mutations support client-generated UUIDs and an
`Idempotency-Key` header. Duplicate submissions return the original result
instead of creating a second record. This is implemented progressively per
domain; device telemetry uses `(deviceId, messageId)` uniqueness.

## Status codes

| Code | Meaning |
|---|---|
| 200 | Successful read/update |
| 201 | Created |
| 204 | Deleted or no content |
| 400 | Validation or malformed request |
| 401 | Missing/invalid/expired authentication |
| 403 | Authenticated but not permitted |
| 404 | Not found |
| 409 | Conflict or duplicate |
| 429 | Rate limited |
| 503 | Dependency not ready |

## Time and provenance

- All timestamps are UTC ISO 8601 strings.
- Sensor readings distinguish `recordedAt` (device time) from `receivedAt`
  (server time).
- Readings carry `source`: `physical`, `simulation`, `manual` or `import`.
- Readings carry `quality`: `good`, `suspect` or `invalid`.

## Documentation

- OpenAPI schema: `/api/schema/`
- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`

"""Structured error responses for every API exception."""

from __future__ import annotations

import logging

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)

_STATUS_CODES = {
    status.HTTP_400_BAD_REQUEST: "validation_error",
    status.HTTP_401_UNAUTHORIZED: "authentication_required",
    status.HTTP_403_FORBIDDEN: "permission_denied",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_429_TOO_MANY_REQUESTS: "rate_limited",
}


def _message_from_detail(detail) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        first = next(iter(detail.values()), None)
        return _message_from_detail(first)
    if isinstance(detail, (list, tuple)):
        return _message_from_detail(detail[0]) if detail else "Request could not be processed."
    return str(detail)


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", None)

    if response is None:
        logger.exception("Unhandled API exception", exc_info=exc)
        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                    "request_id": request_id,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, Http404):
        code = "not_found"
        message = "Resource not found."
    elif isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        code = "authentication_failed"
        message = _message_from_detail(response.data)
    elif isinstance(exc, PermissionDenied):
        code = "permission_denied"
        message = _message_from_detail(response.data)
    elif isinstance(exc, ValidationError):
        code = "validation_error"
        message = _message_from_detail(response.data)
    elif isinstance(exc, APIException):
        code = getattr(exc, "default_code", None) or _STATUS_CODES.get(
            response.status_code, "api_error"
        )
        message = _message_from_detail(response.data)
    else:
        code = _STATUS_CODES.get(response.status_code, "api_error")
        message = _message_from_detail(response.data)

    details = response.data
    if isinstance(details, dict) and set(details.keys()) == {"detail"}:
        details = None

    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": request_id,
            }
        },
        status=(
            status.HTTP_401_UNAUTHORIZED
            if isinstance(exc, (AuthenticationFailed, NotAuthenticated))
            else response.status_code
        ),
        headers=response.headers,
    )

"""Audit logging helpers that never break the primary request."""

from __future__ import annotations

import logging

from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)


def log_event(
    *,
    action: str,
    entity_type: str,
    actor=None,
    entity_id: str = "",
    metadata: dict | None = None,
    request=None,
) -> AuditLog | None:
    try:
        ip_address = None
        user_agent = ""
        request_id = ""
        if request is not None:
            ip_address = request.META.get("REMOTE_ADDR")
            user_agent = request.META.get("HTTP_USER_AGENT", "")[:2000]
            request_id = getattr(request, "request_id", "") or ""
        return AuditLog.objects.create(
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to write audit log for action %s", action)
        return None

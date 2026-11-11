"""Idempotent import of the frontend AppData shape."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.exceptions import ValidationError

from apps.alerts.services import evaluate_reading
from apps.farms.access import accessible_farms, can_write_farm
from apps.farms.models import Farm, FarmMembership, Feeding, Pond
from apps.telemetry.models import ReadingSource, SensorReading


def _client_id(item: dict) -> str:
    value = item.get("id") or item.get("clientId") or item.get("client_id") or ""
    return str(value)[:100]


def _decimal(value, field: str, *, required: bool = False) -> Decimal | None:
    if value is None or value == "":
        if required:
            raise ValidationError({field: "This value is required."})
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError({field: "Use a numeric value."}) from exc


def _timestamp(value) -> datetime:
    if not value:
        return timezone.now()
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value)
    parsed = parse_datetime(text.replace("Z", "+00:00"))
    if parsed is not None:
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    parsed_date = parse_date(text[:10])
    if parsed_date is not None:
        return datetime.combine(parsed_date, time.min, tzinfo=UTC)
    raise ValidationError("Use an ISO-8601 date or datetime.")


def _find_farm(user, reference, aliases: dict[str, Farm]) -> Farm | None:
    key = str(reference or "")
    if not key:
        return None
    if key in aliases:
        return aliases[key]
    queryset = accessible_farms(user)
    try:
        farm = queryset.filter(id=uuid.UUID(key)).first()
    except ValueError:
        farm = None
    if farm is None:
        farm = queryset.filter(client_id=key[:100]).first()
    if farm is not None:
        aliases[key] = farm
        aliases[str(farm.id)] = farm
        if farm.client_id:
            aliases[farm.client_id] = farm
    return farm


def _find_pond(user, reference, aliases: dict[str, Pond]) -> Pond | None:
    key = str(reference or "")
    if not key:
        return None
    if key in aliases:
        return aliases[key]
    queryset = Pond.objects.filter(farm__in=accessible_farms(user))
    try:
        pond = queryset.filter(id=uuid.UUID(key)).first()
    except ValueError:
        pond = None
    if pond is None:
        pond = queryset.filter(client_id=key[:100]).first()
    if pond is not None:
        aliases[key] = pond
        aliases[str(pond.id)] = pond
        if pond.client_id:
            aliases[pond.client_id] = pond
    return pond


def _record_error(errors: list[dict], section: str, index: int, exc: Exception) -> None:
    if isinstance(exc, ValidationError):
        detail = exc.detail
    else:
        detail = str(exc)
    errors.append({"section": section, "index": index, "detail": detail})


@transaction.atomic
def import_app_data(user, payload: dict) -> dict:
    summary = {
        "farms": {"created": 0, "updated": 0},
        "ponds": {"created": 0, "updated": 0},
        "feedings": {"created": 0, "updated": 0},
        "readings": {"created": 0, "updated": 0},
        "ignored": {
            "listings": len(payload.get("listings") or []),
            "messages": len(payload.get("messages") or []),
        },
        "errors": [],
    }
    farm_aliases: dict[str, Farm] = {}
    pond_aliases: dict[str, Pond] = {}

    for reference, farm in (
        (str(farm.id), farm) for farm in accessible_farms(user).select_related("owner")
    ):
        farm_aliases[reference] = farm
        if farm.client_id:
            farm_aliases[farm.client_id] = farm
    for reference, pond in (
        (str(pond.id), pond) for pond in Pond.objects.filter(farm__in=accessible_farms(user))
    ):
        pond_aliases[reference] = pond
        if pond.client_id:
            pond_aliases[pond.client_id] = pond

    for index, item in enumerate(payload.get("farms") or []):
        try:
            name = str(item.get("name") or "").strip()
            if not name:
                raise ValidationError({"name": "Farm name is required."})
            client_id = _client_id(item)
            farm = None
            if client_id:
                farm = Farm.objects.filter(owner=user, client_id=client_id).first()
            if farm is None:
                farm = Farm.objects.create(
                    owner=user,
                    name=name,
                    location=str(item.get("location") or "")[:255],
                    client_id=client_id,
                    metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
                )
                FarmMembership.objects.get_or_create(
                    farm=farm,
                    user=user,
                    defaults={"role": FarmMembership.Role.OWNER},
                )
                summary["farms"]["created"] += 1
            else:
                changed = False
                if farm.name != name:
                    farm.name = name
                    changed = True
                location = str(item.get("location") or "")[:255]
                if location and farm.location != location:
                    farm.location = location
                    changed = True
                if changed:
                    farm.save()
                    summary["farms"]["updated"] += 1
            farm_aliases[str(farm.id)] = farm
            if client_id:
                farm_aliases[client_id] = farm
        except (ValidationError, ValueError, TypeError) as exc:
            _record_error(summary["errors"], "farms", index, exc)

    for index, item in enumerate(payload.get("ponds") or []):
        try:
            name = str(item.get("name") or "").strip()
            if not name:
                raise ValidationError({"name": "Pond name is required."})
            farm = _find_farm(user, item.get("farmId") or item.get("farm_id"), farm_aliases)
            if farm is None:
                raise ValidationError({"farmId": "Farm not found in this account."})
            if not can_write_farm(user, farm):
                raise ValidationError({"farmId": "You cannot add ponds to this farm."})
            client_id = _client_id(item)
            pond = None
            if client_id:
                pond = Pond.objects.filter(farm=farm, client_id=client_id).first()
            data = {
                "name": name,
                "population": int(item.get("population") or 0),
                "length": _decimal(item.get("length"), "length") or Decimal("0"),
                "width": _decimal(item.get("width"), "width") or Decimal("0"),
                "depth": _decimal(item.get("depth"), "depth") or Decimal("0"),
                "species": str(item.get("species") or "")[:100],
                "status": item.get("status") or Pond.Status.ACTIVE,
            }
            if pond is None:
                pond = Pond.objects.create(
                    farm=farm,
                    client_id=client_id,
                    metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
                    **data,
                )
                summary["ponds"]["created"] += 1
            else:
                changed = False
                for field, value in data.items():
                    if getattr(pond, field) != value:
                        setattr(pond, field, value)
                        changed = True
                if changed:
                    pond.save()
                    summary["ponds"]["updated"] += 1
            pond_aliases[str(pond.id)] = pond
            if client_id:
                pond_aliases[client_id] = pond
        except (ValidationError, ValueError, TypeError) as exc:
            _record_error(summary["errors"], "ponds", index, exc)

    for index, item in enumerate(payload.get("feedings") or []):
        try:
            pond = _find_pond(user, item.get("pondId") or item.get("pond_id"), pond_aliases)
            if pond is None:
                raise ValidationError({"pondId": "Pond not found in this account."})
            if not can_write_farm(user, pond.farm):
                raise ValidationError({"pondId": "You cannot add feeding to this pond."})
            amount = _decimal(item.get("amount"), "amount", required=True)
            fed_at = _timestamp(item.get("date") or item.get("fedAt") or item.get("fed_at"))
            client_id = _client_id(item)
            feeding = None
            if client_id:
                feeding = Feeding.objects.filter(pond=pond, client_id=client_id).first()
            if feeding is None:
                feeding = Feeding.objects.create(
                    pond=pond,
                    amount=amount,
                    fed_at=fed_at,
                    note=str(item.get("note") or "")[:255],
                    created_by=user,
                    client_id=client_id,
                )
                summary["feedings"]["created"] += 1
            else:
                changed = False
                if feeding.amount != amount:
                    feeding.amount = amount
                    changed = True
                if feeding.fed_at != fed_at:
                    feeding.fed_at = fed_at
                    changed = True
                if changed:
                    feeding.save()
                    summary["feedings"]["updated"] += 1
        except (ValidationError, ValueError, TypeError) as exc:
            _record_error(summary["errors"], "feedings", index, exc)

    for index, item in enumerate(payload.get("readings") or []):
        try:
            pond = _find_pond(user, item.get("pondId") or item.get("pond_id"), pond_aliases)
            if pond is None:
                raise ValidationError({"pondId": "Pond not found in this account."})
            if not can_write_farm(user, pond.farm):
                raise ValidationError({"pondId": "You cannot add readings to this pond."})
            client_id = _client_id(item)
            measurements = {
                "temperature": _decimal(item.get("temperature"), "temperature"),
                "oxygen": _decimal(item.get("oxygen"), "oxygen"),
                "ph": _decimal(item.get("ph") or item.get("pH"), "ph"),
                "level": _decimal(item.get("level"), "level"),
            }
            if not any(value is not None for value in measurements.values()):
                raise ValidationError("At least one measurement is required.")
            source = item.get("source") or ReadingSource.IMPORT
            valid_sources = {choice.value for choice in ReadingSource}
            if source not in valid_sources:
                source = ReadingSource.IMPORT
            reading = None
            if client_id:
                reading = SensorReading.objects.filter(pond=pond, client_id=client_id).first()
            if reading is None:
                reading = SensorReading.objects.create(
                    pond=pond,
                    source=source,
                    recorded_at=_timestamp(
                        item.get("date") or item.get("recordedAt") or item.get("recorded_at")
                    ),
                    client_id=client_id,
                    raw=item.get("raw") if isinstance(item.get("raw"), dict) else {},
                    metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
                    **measurements,
                )
                summary["readings"]["created"] += 1
                if reading.source != ReadingSource.IMPORT:
                    evaluate_reading(reading)
            else:
                summary["readings"]["updated"] += 0
        except (ValidationError, ValueError, TypeError) as exc:
            _record_error(summary["errors"], "readings", index, exc)

    return summary

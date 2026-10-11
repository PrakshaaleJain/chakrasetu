import hashlib, json
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sqlalchemy import select
from . import models as m
from .config import RULE_VERSION


def fail(code, message, field=None, next_action=None, status=409):
    raise HTTPException(
        status,
        {
            "code": code,
            "message": message,
            "field": field,
            "blocking": True,
            "next_action": next_action,
        },
    )


def get(db, model, id):
    obj = db.get(model, id)
    if obj is None:
        fail("NOT_FOUND", f"{model.__name__} not found", status=404)
    return obj


def dump(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def future(days=0, minutes=0):
    return (
        datetime.now(timezone.utc) + timedelta(days=days, minutes=minutes)
    ).isoformat()


def parse_time(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        fail("VALIDATION_ERROR", "Use an ISO 8601 timestamp with timezone.", status=422)
    if parsed.tzinfo is None:
        fail("VALIDATION_ERROR", "Timestamps must include a timezone.", status=422)
    return parsed.astimezone(timezone.utc)


def expired(value):
    return parse_time(value) <= datetime.now(timezone.utc)


def audit(db, user, kind, obj, action, **data):
    db.add(
        m.AuditEvent(
            actor_id=user.id,
            object_type=kind,
            object_id=obj.id,
            action=action,
            data={"rule_version": RULE_VERSION, **data},
        )
    )


def exception(db, kind, id, category, owner, next_action, severity="MEDIUM", **data):
    existing = db.scalar(
        select(m.ExceptionCase).where(
            m.ExceptionCase.object_type == kind,
            m.ExceptionCase.object_id == id,
            m.ExceptionCase.category == category,
            m.ExceptionCase.status != "CLOSED",
        )
    )
    if existing:
        return existing
    obj = m.ExceptionCase(
        object_type=kind,
        object_id=id,
        category=category,
        severity=severity,
        owner_org_id=owner,
        next_action=next_action,
        due_at=future(days=2),
        data=data,
    )
    db.add(obj)
    db.flush()
    return obj


def idem(db, user, key, operation, payload, fn):
    if not key or len(key) > 120:
        fail(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Provide a unique Idempotency-Key header.",
            status=400,
        )
    fp = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()
    row = db.scalar(
        select(m.IdempotencyRecord).where(
            m.IdempotencyRecord.actor_id == user.id,
            m.IdempotencyRecord.key == key,
            m.IdempotencyRecord.operation == operation,
        )
    )
    if row:
        if row.fingerprint != fp:
            fail("IDEMPOTENCY_CONFLICT", "Key was used with different input.")
        return row.response
    result = fn()
    db.flush()
    response = dump(result) if hasattr(result, "__table__") else result
    db.add(
        m.IdempotencyRecord(
            actor_id=user.id,
            key=key,
            operation=operation,
            fingerprint=fp,
            response=response,
        )
    )
    return response

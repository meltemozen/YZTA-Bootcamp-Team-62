"""Runtime interpretation of user-reported device state."""

import math
from datetime import date, datetime
from zoneinfo import ZoneInfo

from ..schemas import Device

_ISTANBUL = ZoneInfo("Europe/Istanbul")


def _local_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=_ISTANBUL)
    return value.astimezone(_ISTANBUL)


def running_remaining_hours(
    device: Device,
    target: date,
    now: datetime | None = None,
) -> int:
    """Remaining whole hours for a device the user marked as running.

    A stale switch does not suppress future plans forever: the state expires
    after the declared cycle duration.
    """
    if not device.is_running or not device.enabled:
        return 0
    current = _local_time(now or datetime.now(_ISTANBUL))
    if target != current.date():
        return 0
    if device.status_updated_at is None:
        return device.duration_h
    started = _local_time(device.status_updated_at)
    elapsed_h = max((current - started).total_seconds() / 3600, 0.0)
    return max(math.ceil(device.duration_h - elapsed_h), 0)


def is_schedulable(device: Device, target: date, now: datetime | None = None) -> bool:
    return (
        device.enabled
        and (device.flexibility or "shiftable").lower() != "fixed"
        and running_remaining_hours(device, target, now) == 0
    )

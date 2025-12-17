from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, Optional, Set, Tuple

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_LISTEN_HOST,
    CONF_LISTEN_PORT,
    CONF_MAX_ZONES,
    CONF_OFFLINE_TIMEOUT,
    DEFAULT_LISTEN_HOST,
    DEFAULT_LISTEN_PORT,
    DEFAULT_MAX_ZONES,
    DEFAULT_OFFLINE_TIMEOUT,
    CONF_SMS_ENABLE,
    CONF_SMS_LINE,
    CONF_SMS_PHONE,
    CONF_SMS_MSG_ARM,
    CONF_SMS_MSG_DISARM,
    CONF_SMS_COOLDOWN,
    CONF_SMS_OBJECT_FILTER,
    DEFAULT_SMS_ENABLE,
    DEFAULT_SMS_LINE,
    DEFAULT_SMS_PHONE,
    DEFAULT_SMS_MSG_ARM,
    DEFAULT_SMS_MSG_DISARM,
    DEFAULT_SMS_COOLDOWN,
    DEFAULT_SMS_OBJECT_FILTER,
    SIGNAL_NEW_OBJECT,
    SIGNAL_NEW_ZONE,
    SIGNAL_OBJECT_UPDATE,
)
from .event_codes import EVENT_CODES

_LOGGER = logging.getLogger(__name__)

# From manual: 5000 18AAAAQXXXYYZZZ
# We accept: 5 + any 3 digits (00 + 0 usually) + 18 + object + Q + code + part + zone
CONTACT_ID_RE = re.compile(
    r"^5(?P<rcv>\d{2})(?P<line>\d)18(?P<object>\d{4,10})(?P<q>[ER])(?P<code>\d{3})(?P<part>\d{2})(?P<zone>\d{3})$"
)

FIRE_CODES: Set[int] = set(range(110, 119))
PANIC_CODES: Set[int] = set(range(120, 126))
# "Alarm in zone" range used by add-on; keep wide.
ALARM_CODES: Set[int] = set(range(130, 160))
ARM_CODES: Set[int] = set(range(400, 471)) | {441, 442}

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _clean_raw(s: str) -> str:
    s = (s or "").strip().replace(" ", "")
    # keep printable characters only
    s = "".join(ch for ch in s if ch.isprintable())
    return s

@dataclass
class ParsedEvent:
    ts: str
    raw: str
    receiver: int
    line: int
    object_id: str
    qualifier: str
    code: int
    partition: int
    zone: int
    text: str

def parse_contact_id(raw: str) -> ParsedEvent:
    s = _clean_raw(raw)
    m = CONTACT_ID_RE.match(s)
    if not m:
        raise ValueError(f"Unrecognized Contact ID / SurGard string: {s!r}")

    code = int(m.group("code"))
    part = int(m.group("part"))
    zone = int(m.group("zone"))
    text = EVENT_CODES.get(m.group("code"), f"Событие {code:03d}")

    return ParsedEvent(
        ts=_now_iso(),
        raw=s,
        receiver=int(m.group("rcv")),
        line=int(m.group("line")),
        object_id=m.group("object"),
        qualifier=m.group("q"),
        code=code,
        partition=part,
        zone=zone,
        text=text,
    )

@dataclass
class ObjectState:
    object_id: str
    last_ts: float = 0.0
    last_event: Optional[ParsedEvent] = None
    alarm: bool = False
    fire: bool = False
    panic: bool = False
    armed: bool = False
    armed_mode: str = "away"  # away|home
    active_zones: Set[int] = field(default_factory=set)

class IproSurgardHub:
    def __init__(self, hass: HomeAssistant, entry_id: str, options: dict) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.options = options or {}

        self.listen_host = str(self.options.get(CONF_LISTEN_HOST, DEFAULT_LISTEN_HOST) or DEFAULT_LISTEN_HOST)
        self.listen_port = int(self.options.get(CONF_LISTEN_PORT, DEFAULT_LISTEN_PORT) or DEFAULT_LISTEN_PORT)
        self.max_zones = int(self.options.get(CONF_MAX_ZONES, DEFAULT_MAX_ZONES) or DEFAULT_MAX_ZONES)
        self.offline_timeout = int(self.options.get(CONF_OFFLINE_TIMEOUT, DEFAULT_OFFLINE_TIMEOUT) or DEFAULT_OFFLINE_TIMEOUT)

        # Optional SMS via goip4.send_sms
        self.sms_enable = bool(self.options.get(CONF_SMS_ENABLE, DEFAULT_SMS_ENABLE))
        self.sms_line = int(self.options.get(CONF_SMS_LINE, DEFAULT_SMS_LINE) or DEFAULT_SMS_LINE)
        self.sms_phone = str(self.options.get(CONF_SMS_PHONE, DEFAULT_SMS_PHONE) or DEFAULT_SMS_PHONE)
        self.sms_msg_arm = str(self.options.get(CONF_SMS_MSG_ARM, DEFAULT_SMS_MSG_ARM) or DEFAULT_SMS_MSG_ARM)
        self.sms_msg_disarm = str(self.options.get(CONF_SMS_MSG_DISARM, DEFAULT_SMS_MSG_DISARM) or DEFAULT_SMS_MSG_DISARM)
        self.sms_cooldown = int(self.options.get(CONF_SMS_COOLDOWN, DEFAULT_SMS_COOLDOWN) or DEFAULT_SMS_COOLDOWN)
        self.sms_object_filter = str(self.options.get(CONF_SMS_OBJECT_FILTER, DEFAULT_SMS_OBJECT_FILTER) or DEFAULT_SMS_OBJECT_FILTER).strip()

        self._last_sms_ts: dict[tuple[str, str], float] = {}

        self.objects: Dict[str, ObjectState] = {}
        self._zones_known: Set[Tuple[str, int]] = set()

        self._server: Optional[asyncio.AbstractServer] = None
        self._server_task: Optional[asyncio.Task] = None
        self._stopped: bool = False

    def _get_obj(self, object_id: str) -> ObjectState:
        obj = self.objects.get(object_id)
        if obj is None:
            obj = ObjectState(object_id=object_id)
            self.objects[object_id] = obj
            async_dispatcher_send(self.hass, SIGNAL_NEW_OBJECT, object_id)
        return obj

    @callback
    def is_online(self, object_id: str) -> bool:
        obj = self.objects.get(object_id)
        if not obj or not obj.last_ts:
            return False
        return (time.time() - obj.last_ts) < self.offline_timeout

    @callback
    def zone_is_active(self, object_id: str, zone: int) -> Optional[bool]:
        obj = self.objects.get(object_id)
        if not obj:
            return None
        return zone in obj.active_zones

    @callback
    def known_zones(self) -> Set[Tuple[str, int]]:
        return set(self._zones_known)

    @callback
    def apply_event(self, ev: ParsedEvent, peer: str | None = None) -> None:
        if getattr(self, "_stopped", False):
            return
        obj = self._get_obj(ev.object_id)
        prev_armed = getattr(obj, "armed", False)
        obj.last_ts = time.time()
        obj.last_event = ev

        is_new = (ev.qualifier == "E")

        # Dynamic zone entities when we see a zone (1..max_zones)
        if 1 <= ev.zone <= self.max_zones:
            key = (ev.object_id, ev.zone)
            if key not in self._zones_known:
                self._zones_known.add(key)
                async_dispatcher_send(self.hass, SIGNAL_NEW_ZONE, ev.object_id, ev.zone)

        if ev.code in FIRE_CODES:
            obj.fire = is_new
            obj.alarm = is_new
        elif ev.code in PANIC_CODES:
            obj.panic = is_new
            obj.alarm = is_new

        if ev.code in ALARM_CODES and 1 <= ev.zone <= self.max_zones:
            if is_new:
                obj.active_zones.add(ev.zone)
            else:
                obj.active_zones.discard(ev.zone)
            obj.alarm = len(obj.active_zones) > 0

        if ev.code in ARM_CODES:
            # IMPORTANT: For "Open/Close" family (400..409 etc) the qualifier is used like:
            #   E = action happened (opening/disarm)
            #   R = restore/normal (closing/arm)
            # In IPRO manual Q means: E=новое событие/тревога, R=восстановление/норма. 
            # For arm/disarm it behaves as: E -> снято, R -> поставлено.
            if ev.qualifier == "E":
                # Disarm (opening) — also acknowledge/clear any active alarm flags.
                # Otherwise AlarmControlPanel can stay TRIGGERED after снятие.
                obj.armed = False
                obj.active_zones.clear()
                obj.alarm = False
                obj.fire = False
                obj.panic = False
            else:
                obj.armed = True

            # Stay/Home arming codes
            if obj.armed and ev.code in (441, 442):
                obj.armed_mode = "home"
            elif obj.armed:
                obj.armed_mode = "away"

            # Send SMS on transition (optional)
            if obj.armed != prev_armed:
                if obj.armed:
                    self._schedule_sms(ev.object_id, self.sms_msg_arm)
                else:
                    self._schedule_sms(ev.object_id, self.sms_msg_disarm)

        # Cancel alarm (406) clears everything
        if ev.code == 406 and is_new:
            obj.active_zones.clear()
            obj.alarm = False
            obj.fire = False
            obj.panic = False

        async_dispatcher_send(self.hass, SIGNAL_OBJECT_UPDATE, ev.object_id)

        # Also fire HA event bus for automations
        self.hass.bus.async_fire(
            "ipro_surgard_event",
            {
                "entry_id": self.entry_id,
                "peer": peer,
                **asdict(ev),
            },
        )

    
    def sms_ready(self) -> bool:
        """Return True if SMS control is enabled and minimally configured."""
        return bool(self.sms_enable and self.sms_phone)

    def sms_allowed_for_object(self, object_id: str) -> bool:
        """If sms_object_filter is set, allow SMS only for that object."""
        if not self.sms_object_filter:
            return True
        return object_id == self.sms_object_filter

    def schedule_sms(self, object_id: str, message: str) -> None:
        """Fire-and-forget SMS via goip4.send_sms (best-effort).

        We intentionally do NOT block HA. If GOIP4 isn't installed, we only log.
        """
        if not self.sms_ready():
            return
        if not self.sms_allowed_for_object(object_id):
            return
        if not message:
            return

        # Cooldown to prevent burst duplicates
        key = (object_id, message)
        now = time.time()
        last = self._last_sms_ts.get(key, 0.0)
        if self.sms_cooldown > 0 and (now - last) < self.sms_cooldown:
            return
        self._last_sms_ts[key] = now

        async def _call() -> None:
            try:
                if not self.hass.services.has_service("goip4", "send_sms"):
                    _LOGGER.warning(
                        "IPRO SurGard: SMS enabled but service goip4.send_sms not found (object=%s)",
                        object_id,
                    )
                    return
                await self.hass.services.async_call(
                    "goip4",
                    "send_sms",
                    {
                        "line": self.sms_line,
                        "phone": self.sms_phone,
                        "message": message,
                    },
                    blocking=False,
                )
            except Exception as e:
                _LOGGER.warning("IPRO SurGard: failed to send SMS via GOIP4: %r", e)

        self.hass.async_create_task(_call())

    # Backward compatible alias
    def _schedule_sms(self, object_id: str, message: str) -> None:
        self.schedule_sms(object_id, message)

    async def async_start(self) -> None:
        if self._server:
            return
        self._stopped = False
        self._server = await asyncio.start_server(self._handle_client, host=self.listen_host, port=self.listen_port)
        _LOGGER.info("IPRO SurGard: listening on %s:%s", self.listen_host, self.listen_port)

    async def async_stop(self) -> None:
        self._stopped = True
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            _LOGGER.info("IPRO SurGard: server stopped")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        peer_s = None
        try:
            if peer:
                peer_s = f"{peer[0]}:{peer[1]}"
            data = await asyncio.wait_for(reader.read(4096), timeout=30)
            raw = data.decode(errors="ignore").strip()
            if not raw:
                writer.write(b"NAK\r\n")
                await writer.drain()
                return
            ev = parse_contact_id(raw)
            self.apply_event(ev, peer=peer_s)
            writer.write(b"ACK\r\n")
            await writer.drain()
        except asyncio.TimeoutError:
            try:
                writer.write(b"NAK\r\n")
                await writer.drain()
            except Exception:
                pass
        except Exception as e:
            _LOGGER.warning("IPRO SurGard: RX error from %s: %r", peer_s, e)
            try:
                writer.write(b"NAK\r\n")
                await writer.drain()
            except Exception:
                pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

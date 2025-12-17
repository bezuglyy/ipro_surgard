from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_NEW_OBJECT
from .mixins import IproUpdateMixin
from .hub import IproSurgardHub

SENSOR_KINDS = ("last_event_text", "last_event_raw", "last_event_code")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    hub: IproSurgardHub = hass.data[DOMAIN][entry.entry_id]

    def _add_object(object_id: str) -> None:
        entities = [IproObjectSensor(hub, object_id, kind) for kind in SENSOR_KINDS]
        async_add_entities(entities)

    # existing objects
    for object_id in list(hub.objects.keys()):
        _add_object(object_id)

    @callback
    def _new_object(object_id: str) -> None:
        _add_object(object_id)

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_OBJECT, _new_object))

class IproObjectSensor(IproUpdateMixin, SensorEntity):
    _attr_icon = "mdi:shield-home"

    def __init__(self, hub: IproSurgardHub, object_id: str, kind: str) -> None:
        super().__init__(hub, object_id)
        self.kind = kind
        self._attr_unique_id = f"ipro_surgard_{object_id}_{kind}"
        self._attr_translation_key = kind

    @property
    def native_value(self):
        obj = self.hub.objects.get(self.object_id)
        ev = obj.last_event if obj else None
        if not ev:
            return None
        if self.kind == "last_event_text":
            return ev.text
        if self.kind == "last_event_raw":
            return ev.raw
        if self.kind == "last_event_code":
            return ev.code
        return None

    @property
    def extra_state_attributes(self):
        obj = self.hub.objects.get(self.object_id)
        ev = obj.last_event if obj else None
        if not ev:
            return None
        return {
            "ts": ev.ts,
            "qualifier": ev.qualifier,
            "code": ev.code,
            "partition": ev.partition,
            "zone": ev.zone,
            "receiver": ev.receiver,
            "line": ev.line,
        }

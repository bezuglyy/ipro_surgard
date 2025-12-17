from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_NEW_OBJECT, SIGNAL_NEW_ZONE
from .mixins import IproUpdateMixin
from .hub import IproSurgardHub

OBJECT_KEYS = ("connection", "alarm", "fire", "panic", "armed")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    hub: IproSurgardHub = hass.data[DOMAIN][entry.entry_id]

    def _add_object(object_id: str) -> None:
        entities = [IproObjectBinarySensor(hub, object_id, key) for key in OBJECT_KEYS]
        async_add_entities(entities)

    # existing objects
    for object_id in list(hub.objects.keys()):
        _add_object(object_id)

    @callback
    def _new_object(object_id: str) -> None:
        _add_object(object_id)

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_OBJECT, _new_object))

    # existing zones (if any)
    for (object_id, zone) in sorted(hub.known_zones()):
        async_add_entities([IproZoneBinarySensor(hub, object_id, zone)])

    @callback
    def _new_zone(object_id: str, zone: int) -> None:
        async_add_entities([IproZoneBinarySensor(hub, object_id, zone)])

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_ZONE, _new_zone))

class IproObjectBinarySensor(IproUpdateMixin, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, hub: IproSurgardHub, object_id: str, key: str) -> None:
        super().__init__(hub, object_id)
        self.key = key
        self._attr_unique_id = f"ipro_surgard_{object_id}_{key}"
        self._attr_translation_key = key

    @property
    def is_on(self):
        if self.key == "connection":
            return self.hub.is_online(self.object_id)
        obj = self.hub.objects.get(self.object_id)
        if not obj:
            return None
        return getattr(obj, self.key, None)

class IproZoneBinarySensor(IproUpdateMixin, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_icon = "mdi:shield-outline"

    def __init__(self, hub: IproSurgardHub, object_id: str, zone: int) -> None:
        super().__init__(hub, object_id)
        self.zone = int(zone)
        self._attr_unique_id = f"ipro_surgard_{object_id}_zone_{self.zone:03d}"
        self._attr_name = f"Zone {self.zone:03d}"

    @property
    def is_on(self):
        return self.hub.zone_is_active(self.object_id, self.zone)

    @property
    def extra_state_attributes(self):
        obj = self.hub.objects.get(self.object_id)
        if not obj or not obj.last_event:
            return None
        ev = obj.last_event
        return {
            "last_event_ts": ev.ts,
            "last_event_code": ev.code,
            "last_event_text": ev.text,
            "last_event_qualifier": ev.qualifier,
        }

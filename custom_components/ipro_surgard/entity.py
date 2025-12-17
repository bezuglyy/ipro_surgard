from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN
from .hub import IproSurgardHub

class IproSurgardBaseEntity(Entity):
    _attr_has_entity_name = True

    def __init__(self, hub: IproSurgardHub, object_id: str) -> None:
        self.hub = hub
        self.object_id = object_id

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"ipro_{self.object_id}")},
            name=f"IPRO {self.object_id}",
            manufacturer="IPRO",
            model="SurGard",
        )

    @property
    def available(self) -> bool:
        return self.hub.is_online(self.object_id)

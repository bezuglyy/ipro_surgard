from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import SIGNAL_OBJECT_UPDATE
from .entity import IproSurgardBaseEntity

class IproUpdateMixin(IproSurgardBaseEntity):
    async def async_added_to_hass(self) -> None:
        @callback
        def _updated(object_id: str) -> None:
            if object_id == self.object_id:
                self.async_write_ha_state()

        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_OBJECT_UPDATE, _updated))

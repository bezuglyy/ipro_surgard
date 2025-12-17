from __future__ import annotations

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelState,
    AlarmControlPanelEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_NEW_OBJECT
from .hub import IproSurgardHub
from .mixins import IproUpdateMixin


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub: IproSurgardHub = hass.data[DOMAIN][entry.entry_id]

    def _allowed(object_id: str) -> bool:
        # Prefer hub helpers if present (v1.0.9+), otherwise allow all
        if hasattr(hub, "sms_allowed_for_object"):
            return bool(hub.sms_allowed_for_object(object_id))
        return True

    def _add_object(object_id: str) -> None:
        if not _allowed(object_id):
            return
        async_add_entities([IproAlarmPanel(hub, object_id)])

    # If user configured a specific object filter (e.g. 0001), create panel right away
    obj_filter = getattr(hub, "sms_object_filter", "") or ""
    if obj_filter:
        _add_object(obj_filter)

    # Also add already discovered objects that match filter
    for object_id in list(hub.objects.keys()):
        _add_object(object_id)

    @callback
    def _new_object(object_id: str) -> None:
        _add_object(object_id)

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_OBJECT, _new_object))


class IproAlarmPanel(IproUpdateMixin, AlarmControlPanelEntity):
    _attr_icon = "mdi:shield-home-outline"
    _attr_code_arm_required = False

    def __init__(self, hub: IproSurgardHub, object_id: str) -> None:
        super().__init__(hub, object_id)
        self._attr_unique_id = f"ipro_surgard_{object_id}_alarm_panel"
        self._attr_name = "Alarm Panel"

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        # ONLY TWO STATES IN UI:
        # - Armed Away ("Не дома")
        # - Disarmed ("Без охраны")
        if hasattr(self.hub, "sms_ready") and hasattr(self.hub, "sms_allowed_for_object"):
            if self.hub.sms_ready() and self.hub.sms_allowed_for_object(self.object_id):
                return AlarmControlPanelEntityFeature.ARM_AWAY
        return AlarmControlPanelEntityFeature(0)

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        obj = self.hub.objects.get(self.object_id)
        if not obj:
            # No events received yet
            return None

        if getattr(obj, "alarm", False) or getattr(obj, "fire", False) or getattr(obj, "panic", False):
            return AlarmControlPanelState.TRIGGERED

        if getattr(obj, "armed", False):
            return AlarmControlPanelState.ARMED_AWAY

        return AlarmControlPanelState.DISARMED

    @property
    def state(self) -> AlarmControlPanelState | None:  # pragma: no cover
        return self.alarm_state

    def _ensure_control_enabled(self) -> None:
        if not (hasattr(self.hub, "sms_ready") and self.hub.sms_ready()):
            raise HomeAssistantError(
                "Управление выключено. Включи SMS через GOIP4 в Options интеграции IPRO SurGard."
            )
        if hasattr(self.hub, "sms_allowed_for_object") and not self.hub.sms_allowed_for_object(self.object_id):
            raise HomeAssistantError(
                f"Управление разрешено только для объекта {getattr(self.hub, 'sms_object_filter', '') or '—'}."
            )
        if not self.hass.services.has_service("goip4", "send_sms"):
            raise HomeAssistantError("Не найден сервис goip4.send_sms. Проверь GOIP4 UX/интеграцию.")

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        self._ensure_control_enabled()
        if hasattr(self.hub, "schedule_sms"):
            self.hub.schedule_sms(self.object_id, getattr(self.hub, "sms_msg_disarm", "O0"))
            return
        raise HomeAssistantError("В этой версии хаба нет метода schedule_sms(). Обнови интеграцию целиком.")

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        self._ensure_control_enabled()
        if hasattr(self.hub, "schedule_sms"):
            self.hub.schedule_sms(self.object_id, getattr(self.hub, "sms_msg_arm", "O1"))
            return
        raise HomeAssistantError("В этой версии хаба нет метода schedule_sms(). Обнови интеграцию целиком.")

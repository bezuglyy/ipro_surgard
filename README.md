<p align="center">
  <img src="docs/logo.png" alt="IPRO SurGard" width="220">
</p>

# IPRO SurGard — Home Assistant integration (Contact ID / SurGard TCP)

Интеграция поднимает **TCP‑приёмник SurGard / Contact ID** (как у IPRO‑12) и **динамически создаёт сущности** по мере прихода событий.

Также поддерживается **управление постановкой/снятием через SMS** (через GOIP4), чтобы кнопки в карточке `alarm_control_panel` работали “по делу”.

---

## Возможности

- ✅ TCP‑сервер SurGard / Contact ID (локально, без add-on)
- ✅ Автосоздание объектов и зон (динамически)
- ✅ `alarm_control_panel` со статусами `armed_away` / `disarmed` / `triggered`
- ✅ Событие в Event Bus: `ipro_surgard_event`
- ✅ Опционально: управление **O1/O0 по SMS** через сервис `goip4.send_sms`
- ✅ Фильтр управления по объекту (например, только `0001`)

---

## Установка

### Через HACS
1. HACS → Integrations → “Custom repositories”
2. Добавь репозиторий `bezuglyy/ipro_surgard` (тип: **Integration**)
3. Установи и перезапусти Home Assistant

### Вручную
Скопируй папку `custom_components/ipro_surgard` в:
`/config/custom_components/ipro_surgard`

---

## Настройка в Home Assistant

Settings → Devices & Services → Add integration → **IPRO SurGard**

### Основные параметры
- **listen_host**: IP для прослушивания (обычно `0.0.0.0`)
- **listen_port**: TCP порт (например `6601`)
- **max_zones**: максимум зон (например `64`)
- **offline_timeout**: таймаут “нет связи”, сек (например `300`)

### SMS‑управление (опционально, через GOIP4)
Чтобы кнопки “На охране / Без охраны” в UI реально отправляли команды:

- **sms_enable**: включить
- **sms_line**: линия/сим GOIP4 (например `2`)
- **sms_phone**: номер получателя (куда GOIP4 отправляет SMS)
- **sms_msg_arm**: сообщение на постановку (например `O1`)
- **sms_msg_disarm**: сообщение на снятие (например `O0`)
- **sms_cooldown**: защита от дублей (сек)
- **sms_object_filter**: *опционально* — управлять только одним объектом (например `0001`)

> Важно: состояние `alarm_control_panel` меняется **только по входящим событиям от IPRO**.  
> Нажатие кнопки в UI отправляет SMS, а “факт” подтверждает сам прибор событиями.

---

## Что создаётся

Для каждого объекта `AAAA`:

- `binary_sensor.<...>_connection` — связь (по `offline_timeout`)
- `binary_sensor.<...>_armed`
- `binary_sensor.<...>_alarm`, `fire`, `panic`
- `alarm_control_panel.<...>_alarm_panel`
- `sensor.<...>_last_event_text`, `last_event_code`, `last_event_raw`

Для зон создаются `binary_sensor` **только когда зона встретилась в событиях**.

---

## События (Event Bus)

Интеграция публикует событие:

- `ipro_surgard_event`

В `event.data` есть: `object_id`, `qualifier`, `code`, `partition`, `zone`, `raw`, `ts`, `text` и др.

---

## Пример автоматизации (GOIP4 SMS)

Если ты не используешь управление через сам `alarm_control_panel`, можно делать автоматизации на событие:

```yaml
- alias: IPRO 0001 arm -> SMS O1
  trigger:
    - platform: event
      event_type: ipro_surgard_event
  condition:
    - condition: template
      value_template: "{{ trigger.event.data.object_id == '0001' }}"
    - condition: template
      value_template: "{{ trigger.event.data.code in [401,402,403] and trigger.event.data.qualifier == 'E' }}"
  action:
    - action: goip4.send_sms
      data:
        line: 2
        phone: "89156206127"
        message: "O1"
```

---

## Lovelace (плитки в один ряд)

Пример “как на скрине” (нужен `custom:button-card`):

```yaml
type: grid
columns: 5
square: false
cards:
  - type: custom:button-card
    entity: binary_sensor.ipro_0001_safety
    name: Связь
    icon: mdi:lan-connect
    show_state: true
  - type: custom:button-card
    entity: binary_sensor.ipro_0001_safety_5
    name: Охрана
    icon: mdi:shield-lock
    show_state: true
  - type: custom:button-card
    entity: binary_sensor.ipro_0001_safety_2
    name: Тревога
    icon: mdi:alarm-light-outline
    show_state: true
  - type: custom:button-card
    entity: binary_sensor.ipro_0001_safety_3
    name: Пожар
    icon: mdi:fire-alert
    show_state: true
  - type: custom:button-card
    entity: binary_sensor.ipro_0001_safety_4
    name: Паника
    icon: mdi:alert-octagon-outline
    show_state: true
```

---

## Скриншоты

- `docs/screenshots/`

---

## Отладка

- Проверь порт (не занят ли)
- Смотри лог Home Assistant по домену `ipro_surgard`
- Проверь, что сервис `goip4.send_sms` реально существует (Developer Tools → Services)

---

## Лицензия

MIT — см. `LICENSE`.

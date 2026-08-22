# IPRO SurGard

Кастомная интеграция для [Home Assistant](https://www.home-assistant.io) · версия **1.0.9**.

![icon](custom_components/ipro_surgard/brand/icon.png)

| | |
|---|---|
| Домен | `ipro_surgard` |
| Версия | 1.0.9 |
| Тип | custom integration |

## Описание

Приём событий Contact ID от панелей SurGard с сущностями охраны.

## Возможности

- Панель охраны (взять/снять)
- Бинарные датчики (движение, контакты и т.п.)
- Сенсоры и мониторинг состояния

## Установка

1. Скопируйте папку `custom_components/{domain}/` в каталог `custom_components/` конфигурации Home Assistant.
2. Перезапустите Home Assistant.
3. Настройки → Устройства и службы → Добавить интеграцию → **{mname}**.

> Установка через HACS: добавьте репозиторий `https://github.com/bezuglyy/{repo}` как Custom repository (категория Integration).

## Лицензия

MIT

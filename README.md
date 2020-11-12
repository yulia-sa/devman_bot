# Devman Bot

Бот в Telegram, посылающий уведомления о проверке работ на сайте dvmn.org.

## Подготовка

1. Зарегистрироваться на сайте [dvmn.org](https://dvmn.org/) для получения токена к API 
Devman.

2. Создать бота в Telegram: отправить боту `BotFather` команду `/newbot` и следовать инструкциям, в конце будет выдан токен доступа к HTTP API.

3. Узнать `chat_id` пользователя, которому будут отправляться нотификации: в Telegram отправить команду `/start` боту `userinfobot`.

## Установка

1. В директории приложения создать файл настроек `.env` с содержимым:
```#!bash
DEVMAN_TOKEN=<devman_token>
TELEGRAM_BOT_TOKEN=<telegram_bot_token>
TELEGRAM_CHAT_ID=<telegram_chat_id>
```
2. Python3 должен быть уже установлен. 
Затем используйте `pip` (или `pip3`, есть конфликт с Python2) для установки зависимостей:
```#!bash
pip install -r requirements.txt
```
## Запуск на локальной машине
```#!bash
$ python3 bot.py
```
## Цель проекта

Код написан в образовательных целях на онлайн-курсе для веб-разработчиков [dvmn.org](https://dvmn.org/).

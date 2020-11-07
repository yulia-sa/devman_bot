import logging
import os
import requests
import telegram
import time
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DEVMAN_TOKEN = os.getenv("DEVMAN_TOKEN")
LONG_POLLING_URL = "https://dvmn.org/api/long_polling/"
SLEEP = 5
CLIENT_TIMEOUT = 900
LOG_FILE = "bot.log"


def create_logger(log_file, log_level=logging.INFO):
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger_handler = logging.FileHandler(log_file)
    logger_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    logger_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_handler)
    return logger


def send_message(attempt, logger):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

    message_text = '''У вас проверили работу «%title%»\n\n%status%\n\n%url%'''

    lesson_title = attempt["lesson_title"]
    message_text = message_text.replace("%title%", lesson_title)

    is_negative = attempt["is_negative"]
    if is_negative is False:
        message_text = message_text.replace("%status%",
                                            "Преподавателю всё понравилось, можно приступать к следующему уроку!")
    else:
        message_text = message_text.replace("%status%",
                                            "К сожалению, в работе нашлись ошибки.")

    lesson_url = "https://dvmn.org{}".format(attempt["lesson_url"])
    message_text = message_text.replace("%url%", lesson_url)

    bot.send_message(chat_id=CHAT_ID, text=message_text)
    logger.info("Сообщение отправлено.")
    return       


def check_reviews(logger):
    headers = {
        "Authorization": "Token {}".format(DEVMAN_TOKEN)
    }
    params = {}
    last_attempt_timestamp_handled = 0

    while True:
        try:
            logger.debug("headers: {}".format(headers))
            logger.debug("params: {}".format(params))

            response = requests.get(LONG_POLLING_URL, headers=headers, params=params, timeout=CLIENT_TIMEOUT)
            status_code = response.status_code
            if not status_code == requests.codes.ok:
                logger.warning("Ответ сервера: {}".format(status_code))
                time.sleep(SLEEP)
                continue

            response_json = response.json()
            logger.debug("response_json: {}".format(response_json))

            if "timestamp_to_request" in response_json:
                timestamp_to_request = response_json["timestamp_to_request"]
                params.update({"timestamp": timestamp_to_request})

            if response_json["status"] == "found":              
                if last_attempt_timestamp_handled == response_json["last_attempt_timestamp"]:
                    continue
                else:
                    new_attempts = response_json["new_attempts"]
                    for attempt in new_attempts:
                        send_message(attempt, logger)

                last_attempt_timestamp = response_json["last_attempt_timestamp"]
                params.update({"timestamp": last_attempt_timestamp})

        except requests.exceptions.ReadTimeout:
            logger.warning("Произошел таймаут на стороне клиента!")
            continue

        except requests.exceptions.ConnectionError:
            logger.warning("Проблема с соединением!")
            time.sleep(SLEEP)
            continue


def main():
    logger = create_logger(log_file=LOG_FILE, log_level=logging.DEBUG)
    logger.info("Начало работы скрипта")
    check_reviews(logger)


if __name__ == "__main__":
    main()

import logging
import os
import requests
import telegram
import time
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler


logger = logging.getLogger(__file__)


def send_message(attempt, telegram_bot_token, telegram_chat_id):
    bot = telegram.Bot(token=telegram_bot_token)

    message_text = '''У вас проверили работу «%title%»\n\n%status%\n\n%url%'''

    lesson_title = attempt["lesson_title"]
    message_text = message_text.replace("%title%", lesson_title)

    is_negative = attempt["is_negative"]
    if not is_negative:
        message_text = message_text.replace("%status%",
                                            "Преподавателю всё понравилось, можно приступать к следующему уроку!")
    else:
        message_text = message_text.replace("%status%",
                                            "К сожалению, в работе нашлись ошибки.")

    lesson_url = "https://dvmn.org{}".format(attempt["lesson_url"])
    message_text = message_text.replace("%url%", lesson_url)

    bot.send_message(chat_id=telegram_chat_id, text=message_text)
    logger.info("Сообщение отправлено")


def check_reviews(devman_token,
                  long_polling_url,
                  client_timeout,
                  telegram_bot_token,
                  telegram_chat_id,
                  sleep):
    headers = {
        "Authorization": "Token {}".format(devman_token)
    }
    params = {}
    last_attempt_timestamp_handled = 0

    while True:
        try:
            logger.debug("headers: {}".format(headers))
            logger.debug("params: {}".format(params))

            response = requests.get(long_polling_url, headers=headers, params=params, timeout=client_timeout)
            response.raise_for_status()
            
            response_data = response.json()
            logger.debug("response_data: {}".format(response_data))

            status = response_data.get("status")

            if status == "timeout":
                logger.info("Нет новых проверок работ (таймаут)")
                timestamp_to_request = response_data["timestamp_to_request"]
                params.update({"timestamp": timestamp_to_request})

            elif status == "found":
                last_attempt_timestamp = response_data["last_attempt_timestamp"]     

                if last_attempt_timestamp_handled > last_attempt_timestamp:
                    logger.info("Нет новых проверок работ")
                    params.update({"timestamp": last_attempt_timestamp})

                logger.info("Есть новые проверки работ")
                params.update({"timestamp": last_attempt_timestamp})
                new_attempts = response_data["new_attempts"]
                for attempt in new_attempts:
                    send_message(attempt, telegram_bot_token, telegram_chat_id)

            else:
                logger.warning("response_data: {}".format(response_data))
                time.sleep(sleep)

        except requests.exceptions.HTTPError as http_err:
            logger.warning(http_err)
            time.sleep(sleep)

        except requests.exceptions.ReadTimeout as read_timeout_err:
            logger.warning(read_timeout_err)

        except requests.exceptions.ConnectionError as connection_err:
            logger.warning(connection_err)
            time.sleep(sleep)


def main():
    load_dotenv()

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    DEVMAN_TOKEN = os.getenv("DEVMAN_TOKEN")
    LONG_POLLING_URL = "https://dvmn.org/api/long_polling/"
    SLEEP = 5
    CLIENT_TIMEOUT = 900
    LOG_FILE = "bot.log"
    MAX_LOG_FILE_SIZE = 102400
    BACKUP_COUNT = 2
    LOG_LEVEL_CONSOLE = logging.INFO

    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s - %(levelname)s - %(message)s",
                        filename=LOG_FILE,
                        filemode='w')

    RotatingFileHandler(LOG_FILE, maxBytes=MAX_LOG_FILE_SIZE, backupCount=BACKUP_COUNT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL_CONSOLE)
    console_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logger.info("Начало работы скрипта")
    check_reviews(DEVMAN_TOKEN, LONG_POLLING_URL, CLIENT_TIMEOUT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SLEEP)


if __name__ == "__main__":
    main()

import logging
import os
import requests
import telegram
import time
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

LONG_POLLING_URL = "https://dvmn.org/api/long_polling/"
SLEEP = 5
CLIENT_TIMEOUT = 900
LOG_FILE = "bot.log"
MAX_LOG_FILE_SIZE = 102400
BACKUP_COUNT = 2
LOG_LEVEL_CONSOLE = logging.INFO
LOG_LEVEL_BOT = logging.WARNING


def send_message(attempt, bot, telegram_chat_id):
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


def check_reviews(bot,
                  logger,
                  telegram_chat_id,
                  devman_token,
                  long_polling_url,
                  client_timeout,
                  sleep):
    headers = {
        "Authorization": "Token {}".format(devman_token)
    }
    params = {}

    logger.info("Бот запущен")

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
                logger.info("Есть новые проверки работ")
                last_attempt_timestamp = response_data["last_attempt_timestamp"]
                params.update({"timestamp": last_attempt_timestamp})
                new_attempts = response_data["new_attempts"]
                for attempt in new_attempts:
                    send_message(attempt, bot, telegram_chat_id)
                    logger.info("Сообщение о проверке отправлено")

            else:
                logger.warning("Неожиданный ответ от сервера!\nresponse_data: {}".format(response_data))
                time.sleep(sleep)

        except requests.exceptions.HTTPError as http_err:
            logger.warning("Произошла ошибка:\n{}".format(http_err))
            time.sleep(sleep)

        except requests.exceptions.ReadTimeout as read_timeout_err:
            logger.warning("Произошла ошибка:\n{}".format(read_timeout_err))

        except requests.exceptions.ConnectionError as connection_err:
            logger.warning("Произошла ошибка:\n{}".format(connection_err))
            time.sleep(sleep)

        except Exception as exp:
            logger.error(exp, exc_info=True)


def main():
    load_dotenv()

    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    devman_token = os.getenv("DEVMAN_TOKEN")

    bot = telegram.Bot(token=telegram_bot_token)
    bot_logger = telegram.Bot(token=telegram_bot_token)

    class LogsHandler(logging.Handler):

        def __init__(self):
            logging.Handler.__init__(self)
            self.bot_logger = bot_logger
            self.telegram_chat_id = telegram_chat_id

        def emit(self, record):
            log_entry = self.format(record)
            self.bot_logger.send_message(chat_id=self.telegram_chat_id, text=log_entry)

    logger = logging.getLogger(__file__)

    # File logger
    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s - %(levelname)s - %(message)s",
                        filename=LOG_FILE,
                        filemode='w')

    RotatingFileHandler(LOG_FILE, maxBytes=MAX_LOG_FILE_SIZE, backupCount=BACKUP_COUNT)
            
    # Console logger
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL_CONSOLE)
    console_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Telegram logger
    telegram_logs_handler = LogsHandler()
    telegram_logs_handler.setLevel(LOG_LEVEL_BOT)
    logs_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    telegram_logs_handler.setFormatter(logs_formatter)
    logger.addHandler(telegram_logs_handler)

    check_reviews(bot, logger, telegram_chat_id, devman_token, LONG_POLLING_URL, CLIENT_TIMEOUT, SLEEP)


if __name__ == "__main__":
    main()

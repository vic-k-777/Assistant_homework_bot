import telegram
import logging
import requests
import os
import time
import sys
from http import HTTPStatus
from logging import Formatter
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='bot.log',
    format='%(asctime)s,%(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(Formatter(fmt='[%(asctime)s: %(levelname)s] %(message)s'))
logger.addHandler(handler)

logging.debug('Бот запущен в работу.')


def check_tokens():
    """Проверяем доступность переменных окружения"""
    if all([
            PRACTICUM_TOKEN,
            TELEGRAM_TOKEN,
            TELEGRAM_CHAT_ID,
    ]):
        return True


def send_message(bot, message):
    """Отправляем сообщение в чат пользователя в Telegram"""
    try:
        logging.debug(f'Сообщение успешно отправлено в чат'
                      f'{TELEGRAM_CHAT_ID}: {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(f'При отправке сообщения произошла ошибка {error}.')
        raise Exception(f'При отправке сообщения произошла ошибка {error}.')


def get_api_answer(timestamp):
    """делаем запрос к API."""
    """В случае успешного запроса должна вернуть ответ API,"""
    """приведя его из формата JSON к типам данных Python."""
    current_timestamp = int(time.time())
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params
                                         )
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise Exception(f'Ошибка при запросе к основному API: {error}')
    if homework_statuses.status_code != HTTPStatus.OK:
        status_code = homework_statuses.status_code
        logging.error(f'Ошибка {status_code}')
        raise Exception(f'Ошибка {status_code}')
    try:
        return homework_statuses.json()
    except ValueError:
        logger.error('Ошибка парсинга ответа из формата json')
        raise ValueError('Ошибка парсинга ответа из формата json')


def check_response(response):
    """Проверяем ответ API на соответствие документации"""
    """В качестве параметра функция получает ответ API,"""
    """приведенный к типам данных Python"""
    if type(response) is not dict:
        logger.error('Ответ API не является словарем.')
        raise TypeError
    if ('current_date' in response) and ('homeworks' in response):
        if type(response.get('homeworks')) is not list:
            logger.error('Ответ API не соответствует.')
            raise TypeError
        homeworks = response.get('homeworks')
        return homeworks
    else:
        logger.error('Ключи словаря не соответствуют ожиданиям.')
        raise KeyError


def parse_status(homework):
    """извлекаем из инфо о конкретой ДР статус работы."""
    """В качестве параметра функция получает 1 элемент из списка ДР."""
    """В случае успеха, функция возвращает строку,"""
    """содержащую один из вердиктов словаря HOMEWORK_VERDICTS"""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise Exception(f'Неизвестный статус работы: {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует переменная окружения')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                for hw in homeworks:
                    message = parse_status(hw)
                    send_message(bot, message)
            else:
                logger.debug('Нет новых статусов')
            current_timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

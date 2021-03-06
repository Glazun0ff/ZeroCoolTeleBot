# coding=utf-8
import telebot
import requests
import json
import logging
from telebot import types
from pyowm.owm import OWM
from pyowm.utils.config import get_default_config
from datetime import datetime
from bs4 import BeautifulSoup as bs
from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import bot_token, owm_api_key, binance_api_key, binance_api_secret

bot = telebot.TeleBot(bot_token, parse_mode=None)

config_dict = get_default_config()
config_dict['language'] = 'ru'
owm = OWM(owm_api_key, config_dict)
mgr = owm.weather_manager()

cbr_url = 'https://www.cbr.ru/scripts/XML_daily.asp?date_req=' + str(datetime.today().strftime('%d/%m/%Y'))

headers = {'accept': '*/*', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                          '(KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36'}

# add filemode="w" to overwrite
logging.basicConfig(filename='ZeroCoolBot.log', filemode='w', format='%(asctime)s - %(message)s',
                    datefmt='%d %b %y %H:%M:%S', level=logging.INFO)


@bot.message_handler(commands=['start'])
def start_message(message):
    # keyboard
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    btn1 = types.KeyboardButton('Курс $')
    btn2 = types.KeyboardButton('Курсы валют')
    btn3 = types.KeyboardButton('Курс ₿')
    markup.add(btn1, btn2, btn3)

    try:
        send_msg = 'Привет, {0.first_name}!\n' \
                   'Я - <b>{1.first_name}</b>, помогаю узнать погоду и курсы валют.\n' \
                   'Чтобы узнать погоду, введи название города.\n' \
                   'Чтобы узнать курс, нажми соответствующую кнопку.' \
            .format(message.from_user, bot.get_me())
        bot.send_message(message.chat.id, send_msg, parse_mode='html', reply_markup=markup)
    except Exception as e:
        logging.error("Exception occurred in start_message_start", exc_info=e)


@bot.message_handler(content_types=['text'])
def send_echo(message):
    if message.text == 'Курс $':
        print(str(datetime.today().strftime('%d.%m.%Y %H:%M:%S')) + ' Запрос курса валют')
        logging.info('Запрос курса валют')
        bot.send_message(message.chat.id, cbr_parse())
    elif message.text == 'Курсы валют':
        print(str(datetime.today().strftime('%d.%m.%Y %H:%M:%S')) + ' Запрос всех курсов валют')
        logging.info('Запрос всех курсов валют')
        bot.send_message(message.chat.id, cbr_parse_all())
    elif message.text == 'Курс ₿':
        print(str(datetime.today().strftime('%d.%m.%Y %H:%M:%S')) + ' Запрос курса крипты')
        logging.info('Запрос курса крипты')
        bot.send_message(message.chat.id, binance())
    else:  # погода в городах
        try:
            weather = mgr.weather_at_place(message.text).weather
            temp = weather.temperature('celsius')['temp']
            wind = weather.wind()['speed']
            humidity = weather.humidity
            answer = 'В городе ' + message.text + ' сейчас ' + weather.detailed_status + ', температра ' + str(
                temp) + '°, скорость ветра ' + str(wind) + 'м/с, влажность ' + str(humidity) + '%. '
            if temp < 10:
                answer += 'Сейчас холодно, одевайтесь тепло.'
            elif temp < 18:
                answer += 'Сейчас прохладно, одевайтесь теплее.'
            else:
                answer += 'Температура ok, одевайтесь легко.'
            if weather.detailed_status == 'небольшой дождь' \
                    or weather.detailed_status == 'дождь' \
                    or weather.detailed_status == 'гроза':
                answer += ' Не забудьте взять зонт.'
            bot.send_message(message.chat.id, answer)
            print(str(datetime.today().strftime('%d.%m.%Y %H:%M:%S')) + ' Запрос погоды для города ' + message.text)
            logging.info('Запрос погоды для города ' + message.text)
        except Exception as e:
            logging.error('Exception occurred in send_echo_town', exc_info=e)
            answer = 'Город не найден, попробуйте ввести на английском языке'
            bot.send_message(message.chat.id, answer)


def cbr_parse():  # курс 3х валют
    try:
        session = requests.Session()  # видимость того что один пользователь просмтривает много инфы
        request = session.get(cbr_url, headers=headers)  # эмуляция открыия страницы в браузере
        if request.status_code == 200:
            soup = bs(request.content, 'lxml')
            nominals = soup.find_all('nominal')
            names = soup.find_all('name')
            values = soup.find_all('value')
            rate = 'Курс ЦБ России на ' + str(datetime.today().strftime('%d.%m.%Y')) + '\n\n'
            rate += nominals[10].get_text() + ' ' + names[10].get_text() + ' - ' + str(
                round(float(values[10].get_text().replace(',', '.', 1)), 2)) + ' ₽' + '\n'
            rate += nominals[11].get_text() + ' ' + names[11].get_text() + ' - ' + str(
                round(float(values[11].get_text().replace(',', '.', 1)), 2)) + ' ₽' + '\n'
            rate += nominals[27].get_text() + ' ' + names[27].get_text() + ' - ' + str(
                round(float(values[27].get_text().replace(',', '.', 1)), 2)) + ' ₽'
            return rate
        else:
            print('error_cbr_parse')
    except Exception as e:
        logging.error("Exception occurred in cbr_parse", exc_info=e)


# @bot.message_handler(commands=['rate', 'курс'])
# def send_welcome(message):
#     try:
#         answer = cbr_parse()
#         print(str(datetime.today().strftime('%d.%m.%Y %H:%M:%S')) + ' Запрос курса валют')
#         logging.info('Запрос курса валют')
#         bot.send_message(message.chat.id, str(answer))
#     except Exception as e:
#         logging.error('Exception occurred in send_welcome_rate', exc_info=e)


# курс всех валют
def cbr_parse_all():
    try:
        session = requests.Session()  # видимость того что один пользователь просмтривает много инфы
        request = session.get(cbr_url, headers=headers)  # эмуляция открыия страницы в браузере
        if request.status_code == 200:
            soup = bs(request.content, 'lxml')  # получаем весь контент, заменяем html.parser на lxml
            nominals = soup.find_all('nominal')
            names = soup.find_all('name')
            values = soup.find_all('value')
            rate = 'Курс ЦБ России на ' + str(datetime.today().strftime('%d.%m.%Y')) + '\n\n'
            for i in range(0, len(names)):
                rate += nominals[i].get_text() + ' ' + names[i].get_text() + ' - ' + str(
                    round(float(values[i].get_text().replace(',', '.', 1)), 2)) + ' ₽' + '\n'
            return rate
        else:
            print('error_cbr_parse_all')
    except Exception as e:
        logging.error('Exception occurred in cbr_parse_all', exc_info=e)


# @bot.message_handler(commands=['rates', 'курсы'])
# def send_welcome(message):
#     try:
#         answer = cbr_parse_all()
#         # print(answer)
#         print(str(datetime.today().strftime('%d.%m.%Y %H:%M:%S')) + ' Запрос всех курсов валют')
#         logging.info('Запрос всех курсов валют')
#         bot.send_message(message.chat.id, str(answer))
#     except Exception as e:
#         logging.error('Exception occurred in send_welcome_rates', exc_info=e)


# курс крипты
def binance():
    client = Client(binance_api_key, binance_api_secret)
    try:
        # prices = client.get_all_tickers()
        btc = client.get_margin_price_index(symbol='BTCUSDT')
        btc_cp = json.loads(json.dumps(client.get_ticker(symbol='BTCUSDT')))
        eth = client.get_margin_price_index(symbol='ETHUSDT')
        eth_cp = json.loads(json.dumps(client.get_ticker(symbol='ETHUSDT')))
        xrp = client.get_margin_price_index(symbol='XRPUSDT')
        xrp_cp = json.loads(json.dumps(client.get_ticker(symbol='XRPUSDT')))
        bnb = client.get_margin_price_index(symbol='BNBUSDT')
        bnb_cp = json.loads(json.dumps(client.get_ticker(symbol='BNBUSDT')))
        coin = 'Курс криптовалют на ' + str(datetime.today().strftime('%d.%m.%Y %H:%M:%S')) + '\n\n' + \
               'BTC - ' + str(round(float(btc['price']), 2)) + ' $ (' + str(
            round(float(btc_cp["priceChangePercent"]), 2)) + '%)' + '\n' + \
               'ETH - ' + str(round(float(eth['price']), 2)) + ' $ (' + str(
            round(float(eth_cp["priceChangePercent"]), 2)) + '%)' + '\n' + \
               'XRP - ' + str(round(float(xrp['price']), 3)) + ' $ (' + str(
            round(float(xrp_cp["priceChangePercent"]), 2)) + '%)' + '\n' + \
               'BNB - ' + str(round(float(bnb['price']), 3)) + ' $ (' + str(
            round(float(bnb_cp["priceChangePercent"]), 2)) + '%)'
        # time.strftime('%d.%m.%Y %H:%M:%S', time.gmtime(btc['calcTime']/1000.))
        return coin
    except BinanceAPIException as e:
        print(e.status_code)
        print(e.message)
        logging.error("Exception occurred in binance", exc_info=True)


# @bot.message_handler(commands=['coin', 'crypto', 'крипта'])
# def send_welcome(message):
#     try:
#         answer = binance()
#         print(str(datetime.today().strftime('%d.%m.%Y %H:%M:%S')) + ' Запрос курса крипты')
#         logging.info('Запрос курса крипты')
#         bot.send_message(message.chat.id, str(answer))
#     except Exception as e:
#         logging.error('Exception occurred in send_welcome_coin', exc_info=e)


logging.info('ZeroCoolBot запущен')
print('ZeroCoolBot запущен ' + str(datetime.today().strftime('%d.%m.%Y %H:%M:%S')))

bot.polling(none_stop=True)  # бесконечный бот

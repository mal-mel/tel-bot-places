import telebot
import re
from config import token
from telebot import types
from collections import defaultdict
from db import DB
from distance_calculation import calculate

database = DB('users_places.db')

regular = '^[0-9]{,2}\.[0-9]*, [0-9]{,2}\.[0-9]*$'
bot = telebot.TeleBot(token)
START, LOCATION, DESCRIPTION, CONTINUE = range(4)
USER_STATE = defaultdict(lambda: START)
TEMP_LIST = []


def authentication(message):
    """Аутентификация пользователя"""

    user_id = message.from_user.id

    try:
        database.query(f'select user_id from users where user_id={user_id}').fetchall()[0][0]
    except IndexError:
        database.query(f'insert into users values({user_id}, "{message.from_user.username}")')


def add_place(message, location, description):
    """Добавление места в БД"""

    user_id = message.from_user.id

    lon = location.longitude
    lat = location.latitude

    database.query(f'insert into places values("{lon}, {lat}", {user_id}, "{description}")')


def get_state(message):
    return USER_STATE[message.chat.id]


def update_state(message, state):
    USER_STATE[message.chat.id] = state


def create_keyboard(message):
    places = database.query(f'select description from places where user_id={message.from_user.id}').fetchall()

    if len(places) > 10:
        places = places[-10:]

    if len(places) == 0:
        return False

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(text=str(p[0]), callback_data=str(p[0]))
               for p in places]
    keyboard.add(*buttons)

    return keyboard


@bot.message_handler(func=lambda message: get_state(message) == START)
def start_handler(message):
    bot.send_message(message.chat.id, 'Привет, я бот умеющий сохранять твои любимые места и показывать их тебе\n'
                                      'при необходимости!\n\n'
                                      'Список доступных команд:\n'
                                      '/add - Добавить место\n'
                                      '/list - Показать твои места\n'
                                      '/reset - Удаление всех мест')

    authentication(message)

    update_state(message, CONTINUE)


@bot.message_handler(commands=['add'])
def add_handler(message):
    bot.send_message(message.chat.id, 'Для того чтобы добавить место, отправь мне его геолокацию\n'
                                      'Или координаты формата: xx.xxxxxx, yy.yyyyyy')

    update_state(message, LOCATION)


@bot.message_handler(content_types=['location', 'text'], func=lambda message: get_state(message) == LOCATION)
def location_handler(message):
    """В этом хендлере осуществляется проверка на тип переданных координат"""

    if not message.text:
        location = message.location
    elif re.match(regular, message.text):
        location = types.Location
        lon, lat = message.text.split(',')
        location.longitude = float(lon)
        location.latitude = float(lat)
    else:
        bot.send_message(message.chat.id, 'По всей видимости твое сообщение не соответствует шаблону\n'
                                          'Попробуй еще раз')
        return

    for i in database.query(f'select coor from places where user_id={message.from_user.id}').fetchall():
        temp = i[0].split(',')

        if calculate(location.latitude, float(temp[1]), location.longitude, float(temp[0])) <= 500:
            place = database.query(f'select description from places where coor="{i[0]}"').fetchall()[0][0]

            bot.send_message(message.chat.id,
                             f'Тут кстати приблизительно в 500 метрах есть одно из твоих любимых мест:\n'
                             f'{place}')
            break

    TEMP_LIST.append(message)
    TEMP_LIST.append(location)

    bot.send_message(message.chat.id, 'Теперь отправь мне название этого места')

    update_state(message, DESCRIPTION)


@bot.message_handler(func=lambda message: get_state(message) == DESCRIPTION)
def description_handler(message):
    """Добавление места, используется временный список для хранения нужных значений"""

    add_place(TEMP_LIST[0], TEMP_LIST[1], message.text)

    TEMP_LIST.clear()

    bot.send_message(message.chat.id, 'Место успешно добавлено')

    update_state(message, CONTINUE)


@bot.message_handler(commands=['list'], func=lambda message: get_state(message) == CONTINUE)
def list_handler(message):
    """Вывод добавленных мест пользователя"""
    keyboard = create_keyboard(message)

    if keyboard:
        bot.send_message(message.chat.id, 'Список твоих мест:', reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, 'Нет добавленных мест')


@bot.callback_query_handler(func=lambda callback: get_state(callback.message) == CONTINUE)
def callback_place(callback):
    """Хендлер для отправки выбранного места, с проверкой на существование этого места в БД"""

    message = callback.message
    data = callback.data

    try:
        coor = database.query(
            f'select coor from places where user_id={message.chat.id} and description="{data}"').fetchall()
        lon, lat = coor[0][0].split(',')

        bot.send_message(message.chat.id, f'А вот и {data}')
        bot.send_location(message.chat.id, lat, lon)
    except IndexError:
        bot.send_message(message.chat.id, 'Это место удалено')


@bot.message_handler(commands=['reset'])
def reset(message):
    database.query(f'delete from places where user_id={message.from_user.id}')
    bot.send_message(message.chat.id, 'Данные успешно удалены')


bot.polling(none_stop=True)

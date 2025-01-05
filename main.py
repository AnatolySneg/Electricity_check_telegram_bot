import time
import threading
import requests
from telebot import TeleBot
from telebot.types import Message

from settings import TOKEN, DEVICE_IP, CHECK_INTERVAL, MAX_FAIL_COUNT, CHANNEL_ID
from logic.utils import get_avatar_image


bot = TeleBot(TOKEN)

status = None
fail_count = 0
bot_on = False


def check_device():
    try:
        response = requests.get(f"http://{DEVICE_IP}", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def send_notification(new_status):
    global status
    if new_status != status:
        status = new_status
        message = "Электроэнергия доступна ✅" if status else "Электроэнергия отсутствует ❌"
        bot.send_message(CHANNEL_ID, message)
        avatar_image = get_avatar_image(status)
        with open(avatar_image, "rb") as avatar:
            bot.set_chat_photo(chat_id=CHANNEL_ID, photo=avatar)


def monitor_power():
    global fail_count, bot_on
    while True:
        if bot_on:
            is_available = check_device()
            if is_available:
                fail_count = 0
                send_notification(True)

            else:
                fail_count += 1
                if fail_count >= MAX_FAIL_COUNT:
                    send_notification(False)
        time.sleep(CHECK_INTERVAL)


@bot.message_handler(commands=['start_monitoring'])
def start_monitoring(message: Message):
    global bot_on
    if bot_on:
        bot.reply_to(message, "Мониторинг уже включен ✅")
    else:
        bot_on = True
        bot.reply_to(message, "Мониторинг включен ✅")
        threading.Thread(target=monitor_power, daemon=True).start()


@bot.message_handler(commands=['stop_monitoring'])
def stop_monitoring(message: Message):
    global bot_on
    global status
    if not bot_on:
        bot.reply_to(message, "Мониторинг уже выключен ❌")
    else:
        bot_on = False
        status = None
        avatar_image = get_avatar_image(status)
        with open(avatar_image, "rb") as avatar:
            bot.set_chat_photo(chat_id=CHANNEL_ID, photo=avatar)
        bot.reply_to(message, "Мониторинг выключен ❌")


if __name__ == "__main__":
    bot.polling(none_stop=True)

import time
import threading
import requests
from telebot import TeleBot
from telebot.types import Message

from settings import TOKEN, DEVICE_IP, CHECK_INTERVAL, MAX_FAIL_COUNT, CHANNEL_ID, OWNER_ID
from logic.utils import get_avatar_image
from logic.logs_conf import logger


bot = TeleBot(TOKEN)

status = None
fail_count = 0
bot_on = False
monitor_thread = None
lock = threading.Lock()


def check_device():
    try:
        response = requests.get(f"http://{DEVICE_IP}", timeout=5)
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error("Error, during checking device: %s", e)
        return False


def send_notification(new_status):
    global status
    try:
        if new_status != status:
            status = new_status
            message = "Электроэнергия доступна ✅" if status else "Электроэнергия отсутствует ❌"
            bot.send_message(CHANNEL_ID, message)
            avatar_image = get_avatar_image(status)
            with open(avatar_image, "rb") as avatar:
                bot.set_chat_photo(chat_id=CHANNEL_ID, photo=avatar)
    except Exception as e:
        logger.error("Error, during sending notification: %s", e)


def monitor_power():
    global fail_count, bot_on
    try:
        while bot_on:
            is_available = check_device()
            if is_available:
                fail_count = 0
                send_notification(True)
            else:
                fail_count += 1
                if fail_count >= MAX_FAIL_COUNT:
                    send_notification(False)
            time.sleep(CHECK_INTERVAL)
    except Exception as e:
        logger.error("Error, during power monitoring: %s", e)


def check_permission(message):
    if message.from_user.id == int(OWNER_ID):
        return True
    else:
        logger.warning("User @%s, tried to pass a command to bot", message.from_user.username)
        return False


@bot.message_handler(commands=['start_monitoring'])
def start_monitoring(message: Message):
    global bot_on, monitor_thread
    try:
        if check_permission(message):
            with lock:
                if bot_on:
                    bot.reply_to(message, "Мониторинг уже включен ✅")
                else:
                    bot_on = True
                    bot.reply_to(message, "Мониторинг включен ✅")

                    monitor_thread = threading.Thread(target=monitor_power, daemon=True)
                    monitor_thread.start()
        else:
            bot.reply_to(message, "Недостаточно прав для выполнения команды! ❌")
    except Exception as e:
        logger.error("Error, during execution of start_monitoring command: %s", e)


@bot.message_handler(commands=['stop_monitoring'])
def stop_monitoring(message: Message):
    global bot_on, status, monitor_thread
    try:
        if check_permission(message):
            with lock:
                if not bot_on:
                    bot.reply_to(message, "Мониторинг уже выключен ❌")
                else:
                    bot_on = False
                    status = None
                    avatar_image = get_avatar_image(status)
                    with open(avatar_image, "rb") as avatar:
                        bot.set_chat_photo(chat_id=CHANNEL_ID, photo=avatar)
                    bot.reply_to(message, "Мониторинг выключен ❌")
                    if isinstance(monitor_thread, threading.Thread) and monitor_thread.is_alive():
                        monitor_thread.join(timeout=CHECK_INTERVAL)
        else:
            bot.reply_to(message, "Недостаточно прав для выполнения команды! ❌")
    except Exception as e:
        logger.error("Error, during execution of stop_monitoring command: %s", e)


if __name__ == "__main__":
    bot.polling(none_stop=True)

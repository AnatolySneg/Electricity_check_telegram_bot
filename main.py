"""
Telegram Bot for Monitoring Electricity Availability

This script implements a Telegram bot that monitors electricity availability by checking
a network device's accessibility. It sends notifications to a specified channel when
the power status changes and updates the channel's avatar accordingly.

Key Features:
- Continuous monitoring of power availability
- Telegram channel notifications
- Avatar updates based on power status
- Owner-only command access
- Threaded monitoring process

Configuration is handled through settings.py with the following parameters:
- TOKEN: Telegram Bot API token
- DEVICE_IP: IP address of the monitored device
- CHECK_INTERVAL: Time between checks (in seconds)
- MAX_FAIL_COUNT: Number of failed checks before declaring power outage
- CHANNEL_ID: Telegram channel ID for notifications
- OWNER_ID: Telegram user ID of the bot owner
"""

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
    """
    Check if the monitored device is accessible over the network.

    Returns:
        bool: True if device is accessible, False otherwise
    """
    try:
        response = requests.get(f"http://{DEVICE_IP}", timeout=5)
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error("Error, during checking device: %s", e)
        return False


def send_notification(new_status):
    """
    Send power status notification to the Telegram channel and update channel avatar.

    Args:
        new_status (bool): Current power status (True for available, False for unavailable)
    """
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
    """
    Main monitoring loop that continuously checks power status.
    Updates fail count and triggers notifications when necessary.
    Runs in a separate thread when monitoring is active.
    """
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
    """
    Check if the user has permission to execute bot commands.

    Args:
        message (Message): Telegram message object containing user information

    Returns:
        bool: True if user has permission, False otherwise
    """
    if message.from_user.id == int(OWNER_ID):
        return True
    else:
        logger.warning("User @%s, tried to pass a command to bot", message.from_user.username)
        return False


@bot.message_handler(commands=['start_monitoring'])
def start_monitoring(message: Message):
    """
    Handle the /start_monitoring command.
    Starts the power monitoring thread if not already running.
    Only accessible to the bot owner.

    Args:
        message (Message): Telegram message object containing the command
    """
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
    """
    Handle the /stop_monitoring command.
    Stops the power monitoring thread if running.
    Only accessible to the bot owner.

    Args:
        message (Message): Telegram message object containing the command
    """
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

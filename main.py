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
avatar_cache = {}


def check_device():
    """
    Check if the monitored device is accessible over the network.

    Returns:
        bool: True if device is accessible, False otherwise
    """
    try:
        # Увеличиваем timeout и добавляем retry стратегию
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            max_retries=3,  # Количество повторных попыток
            pool_connections=10,
            pool_maxsize=10
        )
        session.mount('http://', adapter)
        
        response = session.head(
            f"http://{DEVICE_IP}", 
            timeout=10,  # Увеличенный timeout
            allow_redirects=True
        )
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error("Error during checking device: %s", e)
        return False
    finally:
        session.close()


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
            
            if new_status not in avatar_cache:
                avatar_image = get_avatar_image(status)
                with open(avatar_image, "rb") as avatar:
                    avatar_cache[new_status] = avatar.read()
            
            bot.set_chat_photo(chat_id=CHANNEL_ID, photo=avatar_cache[new_status])
    except Exception as e:
        logger.error("Error, during sending notification: %s", e)


def monitor_power():
    """
    Main monitoring loop that continuously checks power status.
    Updates fail count and triggers notifications when necessary.
    Runs in a separate thread when monitoring is active.
    """
    global fail_count, bot_on
    local_fail_count = 0
    try:
        while bot_on:
            is_available = check_device()
            if is_available:
                if local_fail_count != 0:
                    with lock:
                        fail_count = 0
                local_fail_count = 0
                send_notification(True)
            else:
                local_fail_count += 1
                if local_fail_count >= MAX_FAIL_COUNT:
                    with lock:
                        fail_count = local_fail_count
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


def run_bot():
    """
    Main bot function that handles bot initialization and polling
    """
    global bot, bot_on, monitor_thread, status
    try:
        bot = TeleBot(TOKEN)
        # Добавляем параметры для более устойчивого соединения
        bot.polling(none_stop=True, 
                   interval=3,           # Интервал между запросами
                   timeout=30,           # Таймаут соединения
                   long_polling_timeout=5)  # Таймаут long polling
    except requests.exceptions.ConnectionError as e:
        logger.error("Connection error occurred: %s", e)
        time.sleep(15)  # Увеличиваем время ожидания перед повторной попыткой
        return False
    except requests.exceptions.ReadTimeout as e:
        logger.error("Timeout error occurred: %s", e)
        time.sleep(10)
        return False
    except Exception as e:
        logger.error("Bot crashed with error: %s", e)
        # Очистка состояния перед перезапуском
        if bot_on:
            bot_on = False
            if isinstance(monitor_thread, threading.Thread) and monitor_thread.is_alive():
                monitor_thread.join(timeout=CHECK_INTERVAL)
        status = None
        time.sleep(10)
        return False
    return True


if __name__ == "__main__":
    retry_count = 0
    max_retries = 5  # Максимальное количество быстрых повторных попыток
    
    while True:
        try:
            if run_bot():
                retry_count = 0  # Сброс счетчика при успешном запуске
                break
            else:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.warning("Maximum retry attempts reached, waiting longer...")
                    time.sleep(60)  # Длительное ожидание после множества попыток
                    retry_count = 0
                logger.info("Restarting bot... (attempt %d/%d)", retry_count, max_retries)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            logger.error("Unexpected error: %s", e)
            time.sleep(30)

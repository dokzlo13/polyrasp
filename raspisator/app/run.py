
# bot.infinity_polling(timeout=10, none_stop=True)

# bot.polling(timeout=10)
import time

from telebot import logger

from raspisator import bot

while True:
    try:
        bot.polling(timeout=40, interval=0, none_stop=True)
    except Exception as e:
        logger.error("Error polling info: \"{0}\"".format(e))
        time.sleep(1)
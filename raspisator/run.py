
# bot.infinity_polling(timeout=10, none_stop=True)

# bot.polling(timeout=10)
import time
import sys, traceback

from telebot import logger, apihelper
from app import bot

# bot.polling(timeout=40, interval=0, none_stop=False)

apihelper.CONNECT_TIMEOUT = 15
# updates = bot.get_updates(offset=(bot.last_update_id + 1), timeout=timeout)
# bot.process_new_updates(updates)


while True:
    try:
        bot.polling(timeout=30, interval=1, none_stop=False)
    except KeyboardInterrupt:
        bot.stop_bot()
        exit(0)
    except Exception as e:
        logger.error("Error polling info: \"{0}\"".format(e))
        exc_info = sys.exc_info()
        traceback.print_exception(*exc_info)
        time.sleep(1)
from loguru import logger

logger.remove()
logger.add("klarki_bot.log")

class audit:
    def info(info_message): 
        logger.info(f'{info_message}')
        
    def error(error_message):
        logger.error(f'{error_message}')

    def warning(error_message):
        logger.warning(f'{error_message}')
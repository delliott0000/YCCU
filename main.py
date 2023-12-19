import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s (%(filename)s) - %(message)s')

try:
    from core.bot import CustomBot
except ModuleNotFoundError as error:
    logging.fatal(f'Missing required dependencies; see requirements.txt - {error}')
    raise SystemExit()


if __name__ == '__main__':

    bot = CustomBot()
    bot.run_bot()

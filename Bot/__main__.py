import logging
from .bot import main
from . import app

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("bot.log"),
            logging.StreamHandler()
        ]
    )

    try:
        # Start the application
        app.start()
        main()
    except Exception as e:
        logging.exception("An error occurred during the execution of the bot")

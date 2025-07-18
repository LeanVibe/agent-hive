import logging


def setup_logger():
    logging.basicConfig(filename=".claude/logs/app.log", level=logging.DEBUG)
    return logging.getLogger("leanvibe")


logger = setup_logger()

if __name__ == "__main__":
    logger.info("Test log")  # Testable: check file
    print("Logger tested")

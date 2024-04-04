import logging

KAI_LOG = logging.getLogger(__name__)
console_handler = logging.StreamHandler()

formatter = logging.Formatter(
    "%(levelname)s - %(asctime)s - [%(filename)s:%(lineno)s - %(funcName)20s()] - %(message)s"
)
console_handler.setFormatter(formatter)
KAI_LOG.addHandler(console_handler)

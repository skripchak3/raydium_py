import logging


class LoggerMixin:
    def init_logger(self, log_format=None):
        log_format = log_format or "[%(asctime)s] %(message)s"
        logging.basicConfig(level=logging.CRITICAL, format=log_format)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)

    def debug(self, msg):
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)

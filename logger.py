import os
import logging
from pathlib import Path
import appdata

DEBUG = logging.DEBUG


class Logger:
    def get(self):
        return 1

    def __init__(self, logFileName, logLevel, consoledebug):
        if not logFileName:
            logFileName = Path('{}/{}.log'.format(os.getcwd(), appdata.PROGRAM_NAME))
        self.logger = logging.getLogger(appdata.PROGRAM_NAME)
        self.logger.setLevel(logLevel)
        formatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
        formatter.default_time_format = '%d.%m.%Y %H:%M:%S'
        formatter.default_msec_format = '%s.%03d'
        fileHandler = logging.FileHandler(logFileName, mode='at', encoding='utf8')
        fileHandler.setLevel(logLevel)
        fileHandler.setFormatter(formatter)
        self.logger.addHandler(fileHandler)
        if consoledebug:
            consoleHandler = logging.StreamHandler()
            consoleHandler.setLevel(logLevel)
            consoleHandler.setFormatter(formatter)
            self.logger.addHandler(consoleHandler)
        self.initialized = True

    def isInitialized(self):
        return self.initialized

    def debug(self, msg):
        self.logger.debug(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def critical(self, msg):
        self.logger.error(msg)

    def fatal(self, msg):
        self.logger.critical(msg)
        exit()

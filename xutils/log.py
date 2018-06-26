# -*- coding: utf-8 -*-

import os
import os.path
import logging

from logging.handlers import RotatingFileHandler


def init(logger=None, level="INFO", file=None, handler_cls=None, process=False,
         max_count=30, propagate=True, file_config=None, dict_config=None):
    # Initialize the argument logger with the arguments, level and log_file.
    if logger:
        fmt = ("%(asctime)s - %(process)d - %(pathname)s - %(funcName)s - "
               "%(lineno)d - %(levelname)s - %(message)s")
        datefmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

        level = getattr(logging, level.upper())

        if file:
            if process:
                filename, ext = os.path.splitext(file)
                if ext:
                    file = "{0}.{1}.{2}".format(filename, os.getpid(), ext)
                else:
                    file = "{0}.{1}".format(filename, os.getpid())
            if handler_cls:
                handler = handler_cls(file, max_count)
            else:
                handler = RotatingFileHandler(file, maxBytes=1024**3, backupCount=max_count)
        else:
            handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(formatter)

        loggers = logger if isinstance(logger, (list, tuple)) else [logger]
        for logger in loggers:
            logger.propagate = propagate
            logger.setLevel(level)
            logger.addHandler(handler)

    # Initialize logging by the configuration file, file_config.
    if file_config:
        logging.config.fileConfig(file_config, disable_existing_loggers=False)

    # Initialize logging by the dict configuration, dict_config.
    if dict_config and hasattr(logging.config, "dictConfig"):
        logging.config.dictConfig(dict_config)

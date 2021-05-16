import logging
from typing import Optional

from shyft.config import Config


def get_logger(name: Optional[str] = None, file_level: Optional[int] = None,
               console_level: Optional[int] = None, config: Optional[Config] = None,
               log_file: Optional[str] = None) -> logging.Logger:
    """Return an appropriately configured Logger instance.

    :param name: The name of the logger. If not specified, this function will create a root logger. In this case,
        `config`, `file_level` and/or `console_level` should be provided so that the root logger can be configured. If
        `name` is specified, in the absence of explicit configuration options, the resulting logger will have the same
        configuration as the root logger.
    :param file_level: What severity level to log to the specified file.
    :param console_level: What severity level to log to the console.
    :param config: A Config object that can be used to configure the logger.
    :param log_file: Path to the file to log to.

    :return: A new, appropriately configured logging.Logger object.
    """

    if name is not None:
        logger = logging.getLogger().getChild(name)
        logger.info(f'Initialised child logger "{name}".')
    else:
        logger = logging.getLogger()
        logger.info('Initialised root logger.')

        if (file_level is not None) and (console_level is not None):
            logger.setLevel(min(file_level, console_level))
        elif file_level is not None:
            logger.setLevel(file_level)
        elif console_level is not None:
            logger.setLevel(console_level)
        else:
            raise ValueError('At least one of `file_level` and `console_level` must be set when initialising root '
                             'logger.')

    if (log_file is None) and (config is not None):
        log_file = config.log_file

    if (file_level is not None) and (log_file is not None):
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(file_level)
        file_fmt = logging.Formatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                     datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)
        logger.info(f'Added file handler for file "{log_file}" to logger.')

    if console_level is not None:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_fmt = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_fmt)
        logger.addHandler(console_handler)
        logger.info(f'Added console handler to logger.')

    return logger





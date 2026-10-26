import datetime
import logging
import os
import sys

from constants import LOG_DIRECTORY


logger = logging.getLogger('Texture Optimizer')


def setup_logger(verbosity):
    """

    Args:
        verbosity(int):

    Returns:

    """
    # Setup logger

    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s [%(lineno)d _%(levelname)s_ %(filename)s] %(message)s')

    # clear prior handlers
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    # Creating stream handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(verbosity)

    # Creating File handler
    if not os.path.exists(LOG_DIRECTORY):
        os.makedirs(LOG_DIRECTORY)
    timestamp = datetime.datetime.now()
    log_name = ''.join(['texture_optimizer', '_', timestamp.strftime("%y%m%d_%H%M")])
    file_handler = logging.FileHandler(
            os.path.join(
                    LOG_DIRECTORY, '{}.log'.format(log_name)
                    ),
            mode = 'a',
            encoding = 'utf-8'
            )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger

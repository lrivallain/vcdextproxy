"""The utils module is a set of functions used in multiple other functions.
"""
import logging.config
import os
import sys
import json

# name the logger for the current module
logger = logging.getLogger(__name__)


env_setting_conf = "VCDEXTPROXY_CONFIGURATION_PATH"


def configure_logger():
    """Initialize and configure a logger for the application.
    """
    # create trivia level (9)
    add_log_level('trivia', 9)
    # create logger
    conf_path = os.environ.get(env_setting_conf)
    with open(os.path.join(conf_path, "logging.json"),
              "r",
              encoding="utf-8") as fd:
        logging.config.dictConfig(json.load(fd))
    # reduce log level for some modules
    logging.captureWarnings(True)


def add_log_level(level_name, level_value, method_name=None):
    """Add a new logging level.

    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    Arguments:
        level_name (str): becomes an attribute of the `logging` module
        level_value (int): value associated to the new log level
        method_name (str, optionnal): becomes a convenience method for both `logging`
            itself and the class returned by `logging.getLoggerClass()` (usually just
            `logging.Logger`). If `method_name` is not specified, `level_name.lower()` is
            used. (Defaults to ``None``)

    Raises:
        AttributeError: To avoid accidental clobberings of existing attributes, this
            method will raise an `AttributeError` if the level name is already an attribute of
            the `logging` module or if the method name is already present.
    """
    if not method_name:
        method_name = level_name.lower()
    if hasattr(logging, level_name):
        raise AttributeError(f"{level_name} is already defined in logging module")
    if hasattr(logging, level_name.upper()):
        raise AttributeError(f"{level_name.upper()} is already defined in logging module")
    if hasattr(logging, method_name):
        raise AttributeError(f"{method_name} is already defined in logging module")
    if hasattr(logging.getLoggerClass(), method_name):
        raise AttributeError(f"{method_name} is already defined in logger class")

    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_value):
            self._log(level_value, message, args, **kwargs)

    def log_to_root(message, *args, **kwargs):
        logging.log(level_value, message, *args, **kwargs)

    logging.addLevelName(level_value, level_name)
    logging.addLevelName(level_value, level_name.upper()) # ALIAS
    setattr(logging, level_name, level_value)
    setattr(logging.getLoggerClass(), method_name, log_for_level)
    setattr(logging, method_name, log_to_root)


def safe_list_get(arr: list, index: int, default: any = None):
    """Safely get a item of list, using default value if out of bounds.

    Arguments:
        arr (list): An array object
        index (int): An index for array lookup
        default (any, optional): A default value to return in case of IndexError
            (Defaults to ``None``)

    Returns:
        any: The value to return (could be the default one)

    Examples:
        >>> safe_list_get(['A','B'], 0, 'C')
        'A'
        >>> safe_list_get(['A','B'], 2, 'C')
        'C'
        >>> safe_list_get(['A','B'], 2)
        None
    """
    try:
        return arr[index]
    except IndexError:
        return default
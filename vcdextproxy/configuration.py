#!/usr/bin/env python
"""Some tools to manage the configuration of the module.
"""

import logging.config
import os
import sys
import json
import yaml
import urllib3
from cachetools import cached, TTLCache
from vcdextproxy.utils import logger


# TODO: avoid this kind of global variables
env_setting_conf = "VCDEXTPROXY_CONFIGURATION_PATH"
config_cache_expire = 300


@cached(TTLCache(maxsize=1000, ttl=config_cache_expire))  # Set in cache for X secondes
def read_configuration():
    """Test environment settings and import config.

    Return value is cached to be available quickly and avoid a lot
        of reads + yaml loading.
    """
    # import configuration from ENV settings
    conf_path = os.environ.get(env_setting_conf)
    if not conf_path:
        logger.critical(
            f"Missing env setting: `{env_setting_conf}`: Example: export {env_setting_conf}=$(pwd)"
        )
        sys.exit(-1)
    if not os.path.isdir(conf_path):
        logger.critical(f"Configuration directory `{conf_path}` is not valid.")
        sys.exit(-2)
    else:
        logger.info(f"Reading configuration from `{conf_path}/config.yml`.")
        with open(os.path.join(conf_path, 'config.yml'), 'r') as conf_file:
            try:
                return yaml.load(conf_file, Loader=yaml.SafeLoader)
            except yaml.YAMLError as e:
                logger.critical(f"YAML parser error when reading the configuration file: {str(e)}")
                exit(-1)
            except Exception as e:
                logger.exception(f"Unmanaged error raised: {str(e)}")
                exit(-1)


MANDATORY = object()  # new unique object
@cached(TTLCache(maxsize=1000, ttl=config_cache_expire))  # Set in cache for X secondes
def get_configuration_item(configuration_item, default=MANDATORY):
    """Get a configuration setting.

    Args:
        configuration_item (str): Name of the setting to retrieve.
        default (any): Default value to provide is nothing is found.
        from_data (dict): a dict to parse for item instead of config file.

    Raise:
        KeyError: Missing mandatory configuration parameter.

    Returns:
        any: Configuration setting or the default value.
    """
    logger.debug(f"Looking for configuration item: {configuration_item}")
    # Append an extra item to local configuration
    if configuration_item == 'global.config_path':
        return os.environ.get(env_setting_conf)
    # Start walking in configuration to look for configuration_item
    config_walker = read_configuration()
    for sub_item in configuration_item.split('.'):
        try:
            config_walker = config_walker[sub_item]
        except KeyError as e:
            if default is MANDATORY:  # mandatory!
                err_msg = f"Missing mandatory configuration parameter: {configuration_item}. "
                err_msg += "Please refer to documentation."
                logger.critical(err_msg)
                raise e
            else:
                logger.debug(f"Returning the default value for configuration item: {configuration_item}")
                return default
    return config_walker


conf = get_configuration_item
"""function: Alias to ``get_configuration_item()``."""


def configure_logger():
    """Initialize and configure a logger for the application.
    """
    # create trivia level (9)
    add_log_level('trivia', 9)
    # create logger
    conf_path = os.environ.get(env_setting_conf)
    with open(
        os.path.join(conf_path, conf("global.log.config_file")),
        "r", encoding="utf-8"
    ) as fd:
        logging.config.dictConfig(json.load(fd))
    # reduce log level for some modules
    logging.captureWarnings(True)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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
        raise AttributeError(
            f"{level_name} is already defined in logging module")
    if hasattr(logging, level_name.upper()):
        raise AttributeError(
            f"{level_name.upper()} is already defined in logging module")
    if hasattr(logging, method_name):
        raise AttributeError(
            f"{method_name} is already defined in logging module")
    if hasattr(logging.getLoggerClass(), method_name):
        raise AttributeError(
            f"{method_name} is already defined in logger class")

    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_value):
            self._log(level_value, message, args, **kwargs)

    def log_to_root(message, *args, **kwargs):
        logging.log(level_value, message, *args, **kwargs)

    logging.addLevelName(level_value, level_name)
    logging.addLevelName(level_value, level_name.upper())  # ALIAS
    setattr(logging, level_name, level_value)
    setattr(logging.getLoggerClass(), method_name, log_for_level)
    setattr(logging, method_name, log_to_root)

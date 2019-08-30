import logging
import sys

# name the logger for the current module
logger = logging.getLogger(__name__)

# managed unhandled Exceptions
def vcdextproxy_excepthook(type, value, traceback):
    """Print the unhandled exceptions.
    """
    logger.error(f"Unhandled exception {str(type)}: {str(value)}")
    logger.error(f"################### Traceback ###################")
    logger.error(f"{str(traceback)}")
    logger.error(f"############### End of Traceback ################")

# Manage clean exit
def signal_handler(signal, frame):
    """Handle a Keyboard Interrupt to leave rabbitMQ connection.
    """
    sys.stdout.write('\b\b\r') # hide the ^C
    logger.info("SIGINT signal catched -> Exiting...")
    sys.exit(0)
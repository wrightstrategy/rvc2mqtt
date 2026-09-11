"""Read the deployment-owned INI without exposing its contents in errors."""

import configparser
from pathlib import Path


class ConfigurationError(Exception):
    """A configuration error safe to report without credential values."""


def load_configuration(path="rvc2mqtt.ini"):
    config = configparser.ConfigParser(inline_comment_prefixes=";")
    try:
        with Path(path).open(encoding="utf-8") as stream:
            config.read_file(stream)
    except (OSError, UnicodeError, configparser.Error):
        raise ConfigurationError(
            "Cannot read rvc2mqtt.ini; provide a valid external INI "
            "(mount it at /app/rvc2mqtt.ini in Docker)"
        ) from None

    required = {
        "General": {"debug": int, "parameterized_strings": int, "screenout": int, "specfile": str},
        "MQTT": {"mqttBroker": str, "mqttUser": str, "mqttPass": str,
                 "mqttOut": int, "mqttOutputTopic": str},
        "CAN": {"CANport": str},
    }
    for section, fields in required.items():
        for name, convert in fields.items():
            try:
                convert(config.get(section, name))
            except (ValueError, configparser.Error):
                raise ConfigurationError(f"Invalid or missing [{section}] {name}") from None
    # Check interpolation now so a malformed password never reaches a traceback.
    try:
        for section in config.sections():
            config.items(section)
    except configparser.Error:
        raise ConfigurationError("Invalid INI interpolation; escape literal % as %%") from None
    try:
        port = config.getint("MQTT", "mqttPort", fallback=1883)
        if not 1 <= port <= 65535:
            raise ValueError
    except (ValueError, configparser.Error):
        raise ConfigurationError("Invalid [MQTT] mqttPort; expected an integer from 1 to 65535") from None
    return config

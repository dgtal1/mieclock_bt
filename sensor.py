"""Support for Xiaomi Mi e-ink Clock, Temperature & Humidity BLE environmental sensor."""
"""Based on great work of @h4 - https://github.com/h4/LYWSD02-home-assistant/issues"""
import logging

from datetime import timedelta
import voluptuous as vol

from lywsd02 import Lywsd02Client as Client

from homeassistant.util import Throttle
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_MAC,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_BATTERY,
)


_LOGGER = logging.getLogger(__name__)

CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_UPDATE_INTERVAL = 30
DEFAULT_NAME = "Mi eClock BT"

# Sensor types are defined like: Name, units
SENSOR_TYPES = {
    "temperature": [DEVICE_CLASS_TEMPERATURE, "Temperature", "°C"],
    "humidity": [DEVICE_CLASS_HUMIDITY, "Humidity", "%"],
    "battery": [DEVICE_CLASS_BATTERY, "Battery", "%"],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_MAC): cv.string,
        vol.Optional(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)): vol.All(
            cv.ensure_list, [vol.In(SENSOR_TYPES)]
        ),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): cv.positive_int,
    }
)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=DEFAULT_UPDATE_INTERVAL)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the MieClockBt sensor."""

    global MIN_TIME_BETWEEN_UPDATES
    MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=config.get(CONF_UPDATE_INTERVAL))

    mac = config.get(CONF_MAC)

    # Configure the client.
    client = Client(mac)

    poller = MieClockData(client)

    devs = []

    for parameter in config[CONF_MONITORED_CONDITIONS]:
        device = SENSOR_TYPES[parameter][0]
        name = SENSOR_TYPES[parameter][1]
        unit = SENSOR_TYPES[parameter][2]

        prefix = config.get(CONF_NAME)
        if prefix:
            name = f"{prefix} {name}"

        devs.append(
            MieClockBtSensor(poller, parameter, device, name, unit)
        )

    add_entities(devs)


class MieClockBtSensor(Entity):
    """Implementing the MieClockBt sensor."""

    def __init__(self, poller, parameter, device, name, unit):
        """Initialize the sensor."""
        self.parameter = parameter
        self._device = device
        self._unit = unit
        self._name = name
        self._state = None
        self._poller = poller

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return self._unit

    @property
    def device_class(self):
        """Device class of this entity."""
        return self._device

    def update(self):
        """Update the sensor."""
        # Send update "signal" to the component
        self._poller.update_data()

        # Get new data (if any)
        updated = self._poller.data

        # Check the data and update the value.
        self._state = updated.get(self.parameter)


class MieClockData:
    """This class handles communication and stores the data."""

    def __init__(self, client: Client):
        """Initialize the class."""
        self.client = client
        self.data = {}

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update_data(self):
        import decimal
        from decimal import Decimal

        decimal.getcontext().rounding = decimal.ROUND_DOWN

        """Update data."""
        # This is where the main logic to update platform data goes.
        try:
            self.data = {
                'temperature': Decimal(self.client.temperature).quantize(Decimal("1.0")),
                'humidity': self.client.humidity,
                'battery': self.client.battery,
            }
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error("Could not update data - %s", error)

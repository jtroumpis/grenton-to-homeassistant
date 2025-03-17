import aiohttp
from .const import (
    DOMAIN,
    CONF_API_ENDPOINT,
    CONF_GRENTON_ID,
    CONF_OBJECT_NAME,
    CONF_GRENTON_TYPE,
    CONF_DEVICE_CLASS,
    CONF_STATE_CLASS,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_GRENTON_TYPE_DEFAULT_SENSOR,
    CONF_GRENTON_TYPE_MODBUS_RTU,
    CONF_GRENTON_TYPE_MODBUS_VALUE,
    CONF_GRENTON_TYPE_MODBUS,
    CONF_GRENTON_TYPE_MODBUS_CLIENT,
    CONF_GRENTON_TYPE_MODBUS_SERVER,
    CONF_GRENTON_TYPE_MODBUS_SLAVE_RTU
)
import logging
import json
import voluptuous as vol
import re
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    PLATFORM_SCHEMA
)
from homeassistant.const import (STATE_ON, STATE_OFF)


_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_ENDPOINT): str,
    vol.Required(CONF_GRENTON_ID): str,
    vol.Required(CONF_GRENTON_TYPE, default=CONF_GRENTON_TYPE_DEFAULT_SENSOR): str, #DEFAULT_SENSOR, MODBUS_RTU, MODBUS_VALUE, MODBUS, MODBUS_CLIENT, MODBUS_SLAVE_RTU
    vol.Optional(CONF_OBJECT_NAME, default='Grenton Sensor'): str,
})


async def async_setup_entry(hass, config_entry, async_add_entities):
    device = config_entry.data

    api_endpoint = device.get(CONF_API_ENDPOINT)
    grenton_id = device.get(CONF_GRENTON_ID)
    grenton_type = device.get(CONF_GRENTON_TYPE)
    object_name = device.get(CONF_OBJECT_NAME)
    
    async_add_entities([GrentonBinarySensor(api_endpoint, grenton_id, grenton_type, object_name)], True)
    
    
class GrentonBinarySensor(BinarySensorEntity):
    def __init__(self, api_endpoint, grenton_id, grenton_type, object_name):
        self._api_endpoint = api_endpoint
        self._grenton_id = grenton_id
        self._grenton_type = grenton_type
        self._object_name = object_name
        self._unique_id = f"grenton_{grenton_id.split('->')[1] if '->' in grenton_id else grenton_id}"
        self._state = None

    @property
    def name(self):
        return self._object_name

    @property
    def unique_id(self):
        return self._unique_id  

    @property
    def is_on(self):
        return self._state == STATE_ON

    async def async_update(self):
        try:
            if len(self._grenton_id.split('->')) == 1:
                command = {"status": f"return getVar(\"{self._grenton_id}\")"}
            elif re.fullmatch(r"[A-Z]{3}\d{4}", self._grenton_id.split('->')[1]):
                grenton_type_mapping = {
                    CONF_GRENTON_TYPE_MODBUS: 14,
                    CONF_GRENTON_TYPE_MODBUS_VALUE: 20,
                    CONF_GRENTON_TYPE_MODBUS_RTU: 22,
                    CONF_GRENTON_TYPE_MODBUS_CLIENT: 19,
                    CONF_GRENTON_TYPE_MODBUS_SERVER: 10,
                    CONF_GRENTON_TYPE_MODBUS_SLAVE_RTU: 10
                }
                index = grenton_type_mapping.get(self._grenton_type, 0)
                command = {"status": f"return {self._grenton_id.split('->')[0]}:execute(0, '{self._grenton_id.split('->')[1]}:get({index})')"}
            else:
                command = {"status": f"return {self._grenton_id.split('->')[0]}:execute(0, 'getVar(\"{self._grenton_id.split('->')[1]}\")')"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self._api_endpoint}", json=command) as response:
                    response.raise_for_status()
                    data = await response.json()
                    self._state = STATE_OFF if data.get("status") == 0 else STATE_ON
        except aiohttp.ClientError as ex:
            _LOGGER.error(f"Failed to update the sensor value: {ex}")
            self._native_value = None

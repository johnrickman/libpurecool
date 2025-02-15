"""Dyson Pure Cool Link library."""

# pylint: disable=too-many-public-methods,too-many-instance-attributes

import logging

import requests
from requests.auth import HTTPBasicAuth

import urllib3

from .dyson_pure_cool import DysonPureCool
from .dyson_pure_hotcool import DysonPureHotCool
from .utils import is_360_eye_device, \
    is_heating_device, is_dyson_pure_cool_device, is_heating_device_v2

from .dyson_360_eye import Dyson360Eye
from .dyson_pure_cool_link import DysonPureCoolLink
from .dyson_pure_hotcool_link import DysonPureHotCoolLink
from .exceptions import DysonNotLoggedException

_LOGGER = logging.getLogger(__name__)

DYSON_API_URL = "appapi.dyson.com"
DYSON_API_URL_CN = "appapi.dyson.cn"
DYSON_API_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"


class DysonAccount:
    """Dyson account."""

    def __init__(self, email, password, country):
        """Create a new Dyson account.

        :param email: User email
        :param password: User password
        :param country: 2 characters language code
        """
        self._email = email
        self._password = password
        self._country = country
        self._logged = False
        self._auth = None
        self._headers = {'User-Agent': DYSON_API_USER_AGENT}
        if country == "CN":
            self._dyson_api_url = DYSON_API_URL_CN
        else:
            self._dyson_api_url = DYSON_API_URL

    def login(self):
        """Login to dyson web services."""
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        _LOGGER.debug("Disabling insecure request warnings since "
                      "dyson are using a self signed certificate.")

        request_body = {
            "email": self._email,
            "password": self._password
        }
        login = requests.post(
            "https://{0}/apiman-gateway/dyson/session/1.0/login".format(self._dyson_api_url),
            headers=self._headers,
            data=request_body,
            verify=False
        )
        # pylint: disable=no-member
        if login.status_code == requests.codes.ok:
            json_response = login.json()
            self._auth = HTTPBasicAuth(json_response["Account"],
                                       json_response["Password"])
            self._logged = True
        else:
            self._logged = False
        return self._logged

    def devices(self):
        """Return all devices linked to the account."""
        if self._logged:
            device_response = requests.get(
                "https://{0}/v1/provisioningservice/manifest".format(
                    self._dyson_api_url),
                headers=self._headers,
                verify=False,
                auth=self._auth)
            device_v2_response = requests.get(
                "https://{0}/v2/provisioningservice/manifest".format(
                    self._dyson_api_url),
                headers=self._headers,
                verify=False,
                auth=self._auth)
            devices = []
            for device in device_response.json():
                if is_360_eye_device(device):
                    dyson_device = Dyson360Eye(device)
                elif is_heating_device(device):
                    dyson_device = DysonPureHotCoolLink(device)
                else:
                    dyson_device = DysonPureCoolLink(device)
                devices.append(dyson_device)

            for device_v2 in device_v2_response.json():
                if is_dyson_pure_cool_device(device_v2):
                    devices.append(DysonPureCool(device_v2))
                elif is_heating_device_v2(device_v2):
                    devices.append(DysonPureHotCool(device_v2))

            return devices

        _LOGGER.warning("Not logged to Dyson Web Services.")
        raise DysonNotLoggedException()

    @property
    def logged(self):
        """Return True if user is logged, else False."""
        return self._logged

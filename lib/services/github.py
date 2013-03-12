import logging
import requests
import json
from getpass import getpass

from lib.service import Service, requires_authentication,\
                        invalidates_cache, cached_property

log = logging.getLogger(__name__)

#   Fix annoying log output.
logging.getLogger('requests').setLevel(logging.WARNING)


class Github(Service):
    """
    Manages the "Name", "Location", "Company" and "Bio" attributes of a Github account.
    """

    def __init__(self, username, password=None):
        """
        Creates a new Github service object.
        Note: the "username" parameter is not given a default value -
              this means that if it is not specified in accounts.yml, it will
              throw an error.
        """
        self.username = username
        self.password = password

    @cached_property
    def user(self):
        u = self.username
        return requests.get("https://api.github.com/"
                            "users/%s" % u).json()

    def authenticate(self, browser):
        if not self.password:
            self.password = getpass("Please enter the Github password "
                                    "for the account %s: " % self.username)
            if self.password == "":
                raise RuntimeError('No password supplied, exiting.')

    def check_name(self):
        return self.user['name']

    def check_location(self):
        return self.user['location']

    def check_company(self):
        return self.user['company']

    def check_biography(self):
        return self.user['bio']

    def modify_name(self, value):
        self.modify_profile_attribute('name', value)

    def modify_location(self, value):
        self.modify_profile_attribute('location', value)

    def modify_company(self, value):
        self.modify_profile_attribute('company', value)

    def modify_biography(self, value):
        self.modify_profile_attribute('bio', value)

    @invalidates_cache
    @requires_authentication
    def modify_profile_attribute(self, name, value):
        url = "https://api.github.com/user"
        auth = (self.username, self.password)
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        payload = {}
        payload[name] = value
        data = json.dumps(payload)
        resp = requests.patch(url=url, auth=auth, headers=headers, data=data)
        if resp.status_code != 200:
            raise RuntimeError("Update failed with a %s error!" %
                               resp.status_code)

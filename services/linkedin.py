import re
import time
import logging
import requests
import pycountry
from bs4 import BeautifulSoup
from getpass import getpass

from lib.service import Service, requires_authentication,\
                        invalidates_cache, cached_property

log = logging.getLogger(__name__)

#   Fix annoying log output.
logging.getLogger('requests').setLevel(logging.WARNING)


class LinkedIn(Service):
    LOGIN_AT = "https://www.linkedin.com/"
    USER_ENDPOINT = "http://www.linkedin.com/in/%s"
    FORM_ENDPOINT = "https://www.linkedin.com/profile/edit-basic-info"

    def __init__(self, email, username, password=None):
        self.email = email
        self.username = username
        self.password = password

    @cached_property
    def user(self):
        resp = requests.get(self.USER_ENDPOINT % self.username)
        bs = BeautifulSoup(resp.text)
        u = {}
        u['name'] = bs.find('span', { 'class' : 'given-name' }).string + " " \
                  + bs.find('span', { 'class' : 'family-name' }).string
        u['headline'] = bs.find('p', { 'class' : 'headline-title' }).string
        u['location'] = bs.find('span', {'class' : 'locality' }).string
        return u

    def authenticate(self, browser):
        if not self.password:
            self.password = getpass("Please enter the LinkedIn password "
                                    "for the account %s: " % self.email)
            if self.password == "":
                raise RuntimeError('No password supplied, exiting.')

        browser.set_handle_robots(False)
        browser.set_handle_refresh(False)
        page = browser.open(self.LOGIN_AT)
        form = [f for f in browser.forms() if f.name == 'login'][0]
        form['session_key'] = self.email
        form['session_password'] = self.password
        resp = browser.open(form.click())
        if 'home' not in resp.geturl():
            raise RuntimeError("Login to %s failed!" % self.__class__.__name__)

        return browser

    def check_name(self):
        return self.user['name'].strip()

    def check_headline(self):
        return self.user['headline'].strip()

    def check_location(self, old):
        new_region = self.user['location'].strip()
        old_region = old['region']
        return bool(re.match(old_region, new_region))

    def modify_name(self, value):
        name = value.split(' ')
        self.modify_profile_attributes( ['firstName', 'lastName'],
                                        [name[0], name[1]])

    def modify_headline(self, value):
        self.modify_profile_attributes( ['headline'], value)

    def modify_location(self, value):
        country = value['country']
        postal_code = value['postal_code']
        country_code = pycountry.countries.get(name=country).alpha2.lower()
        self.modify_profile_attributes( ['countryCode', 'postalCode'],
                                        [[country_code], str(postal_code)])

    @invalidates_cache
    @requires_authentication
    def modify_profile_attributes(self, names, values):
        resp = self.browser.open(self.FORM_ENDPOINT)
        form = [f for f in self.browser.forms() if f.name == 'editBasicInfoForm'][0]
        for i, name in enumerate(names):
          form[name] = values[i]

        resp = self.browser.open(form.click())
        if resp.code != 200:
            raise RuntimeError("Update failed with a %s error!" %
                               resp.status_code)
        log.info("Waiting for %s value to propagate to the API...", "location")
        time.sleep(60)


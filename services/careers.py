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


class Careers(Service):
    LOGIN_AT = "http://careers.stackoverflow.com/users/login"
    USER_ENDPOINT = "http://careers.stackoverflow.com/%s"
    EDIT_ENDPOINT = "http://careers.stackoverflow.com/cv/edit/"

    def __init__(self, email, username, password=None):
        self.email = email
        self.username = username
        self.password = password

    @cached_property
    def user(self):
        resp = requests.get(self.USER_ENDPOINT % self.username)
        bs = BeautifulSoup(resp.text)
        profile_soup = bs.find('div', { 'id' : 'section-personal' })
        u = {}
        u['name'] = profile_soup.find('h1') \
                                .string.strip()
        u['location'] = profile_soup.find('div', { 'class' : None }) \
                                      .find('p', { 'class' : None }) \
                                      .string.strip()
        u['website'] = profile_soup.find('p', { 'id' : 'website' }) \
                                   .find('a', { 'class' : None }) \
                                   .string.strip()
        u['twitter'] = profile_soup.find('a', { 'class' : 'twitter' }) \
                                   .string.strip()
        return u

    def authenticate(self, browser):
        if not self.password:
            self.password = getpass("Please enter the Careers password "
                                    "for the account %s: " % self.email)
            if self.password == "":
                raise RuntimeError('No password supplied, exiting.')

        browser.set_handle_robots(False)
        browser.set_handle_refresh(False)
        browser.addheaders = [
            ('Host', 'openid.stackauth.com'),
            ('Origin', 'http://careers.stackoverflow.com'),
            ('Referer', 'http://careers.stackoverflow.com/users/login')]

        browser.open(self.LOGIN_AT)
        form = [f for f in browser.forms()][0]
        form['username'] = self.email
        form['password'] = self.password
        resp = browser.open(form.click())
        if 'AuthFailed' in resp.geturl():
            raise RuntimeError("Login to %s failed!" % self.__class__.__name__)
        return browser

    def check_name(self):
        return self.user['name']

    # Note: Careers does some interpretting of your location input.
    # - If this check fails because of that, you will need to use location
    #   input data that Careers will expect and accept.
    def check_location(self, old):
        old_str = (old['city'] + ", " + old['state'] + ", " + old['country'])
        return old_str == self.user['location']

    def check_website(self):
        return self.user['website']

    def check_twitter(self, old):
        return self.user['twitter'] == old or self.user['twitter'] == "@%s" % old

    def modify_name(self, value):
        self.modify_profile_attributes(['Name'], [value])

    def modify_location(self, value):
        city = value['city']
        state = value['state']
        country = value['country']
        country_code = pycountry.countries.get(name=country).alpha2.upper()
        self.modify_profile_attributes(
            ['MailingCity', 'MailingRegion', 'MailingCountryCode'],
            [city, state, [country_code]])

    def modify_website(self, value):
        if value[0:6] != 'http://':
          value = "http://%s" % value
        self.modify_profile_attributes(['WebsiteUrl'], [value])

    def modify_twitter(self, value):
        if value[0] == '@':
          value = value[1:]
        self.modify_profile_attributes(['Twitter'], [value])

    @invalidates_cache
    @requires_authentication
    def modify_profile_attributes(self, names, values):
        resp = self.browser.open(self.EDIT_ENDPOINT)
        resp = self.browser.open(resp.geturl() + "?FormName=Personal")
        form = [f for f in self.browser.forms()][0]
        for i, name in enumerate(names):
            form[name] = values[i]
        resp = self.browser.open(form.click())
        if resp.code != 200:
            raise RuntimeError("Update failed with a %s error!" %
                               resp.status_code)


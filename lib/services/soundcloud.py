import time
import logging
import requests
import pycountry
from getpass import getpass

from lib.service import Service, requires_authentication,\
                        invalidates_cache, cached_property

log = logging.getLogger(__name__)

#   Fix annoying log output.
logging.getLogger('requests').setLevel(logging.WARNING)


class SoundCloud(Service):
    LOGIN_AT = "https://soundcloud.com/login?return_to=%2Fsettings"
    USER_ENDPOINT = "http://api.soundcloud.com/users/%s.json?client_id=%s"
    BASIC_PROFILE_ENDPOINT = "http://soundcloud.com/settings"
    BIO_PROFILE_ENDPOINT = "http://soundcloud.com/settings/advanced"
    CLIENT_KEY = "beed65c73fb88ced2a3654e4220ebb83"

    def __init__(self, username, _soundcloud_session):
        self.username = username
        self.soundcloud_session = _soundcloud_session

    @cached_property
    def user(self):
        url = self.USER_ENDPOINT % (self.username, self.CLIENT_KEY)
        print requests.get(url).json()
        return requests.get(url).json()

    def authenticate(self, browser):
        browser.open(self.BASIC_PROFILE_ENDPOINT)
        browser.set_cookie("_soundcloud_session=%s;" % self.soundcloud_session)
        return browser

    def broken_login(self, browser):
        """
        If anybody can get this working, I'd be mighty grateful.
        """
        if not self.password:
            self.password = getpass("Please enter the %s password "
                                    "for the account %s: " %
                                    (self.__class__.__name__, self.username))
            if self.password == "":
                raise RuntimeError('No password supplied, exiting.')
        browser.open(self.LOGIN_AT)
        browser.form = [f for f in browser.forms()
                        if f.attrs.get('id', None) \
                                == 'login-form'][0]
        #   Fill out our form
        browser.form['username'] = self.username
        browser.form['password'] = self.password

        resp = browser.submit()
        if 'captcha' in resp.geturl():
            raise RuntimeError("Captcha'd. Please log in manually via web.")
        assert resp.geturl() == self.BASIC_PROFILE_ENDPOINT
        return browser

    def check_name(self):
        return self.user['username']

    def check_city(self):
        return self.user['city']

    def check_country(self):
        print "checking country, currently %s" % self.user['country']
        return self.user['country']

    def check_biography(self):
        return self.user['description'].replace("\n", "")

    def modify_name(self, value):
        self.modify_profile_attribute('username', value)

    def modify_city(self, value):
        self.modify_profile_attribute('city', value)

    def modify_country(self, value):
        country_code = pycountry.countries.get(name=value).alpha2
        self.modify_profile_attribute('country_code', [country_code])

    @invalidates_cache
    @requires_authentication
    def modify_biography(self, value):
        self.browser.open(self.BIO_PROFIOLE_ENDPOINT)
        self.browser.form = [f for f in self.browser.forms()
                             if f.attrs.get('id', None) \
                                     == 'settings-form'][0]
        self.browser['user[description]'] = value
        resp = self.browser.submit()
        if resp.code != 200:
            raise RuntimeError("Update failed with a %s error!" % resp.code)
        log.info("Waiting for biography value to propagate to the API...")
        time.sleep(60)

    @invalidates_cache
    @requires_authentication
    def modify_profile_attribute(self, name, value):
        self.browser.open(self.BASIC_PROFILE_ENDPOINT)
        self.browser.form = [f for f in self.browser.forms()
                             if f.attrs.get('id', None) \
                                     == 'basic-profile-form'][0]
        self.browser['user[%s]' % name] = value
        resp = self.browser.submit()
        if resp.code != 200:
            raise RuntimeError("Update failed with a %s error!" % resp.code)
        log.info("Waiting for %s value to propagate to the API...", name)
        time.sleep(60)

import logging
import requests
from getpass import getpass

from lib.service import Service, requires_authentication,\
                        invalidates_cache, cached_property

log = logging.getLogger(__name__)

#   Fix annoying log output.
logging.getLogger('requests').setLevel(logging.WARNING)


class Twitter(Service):
    """
    A good example of a service.
    Manages the "Name", "Location" and "Bio" attributes of a Twitter account.
    """

    LOGIN_AT = "https://twitter.com/login?redirect_after_login=%2Fsettings"

    def __init__(self, username, password=None):
        """
        Creates a new Twitter service object.
        Note: the "username" parameter is not given a default value -
              this means that if it is not specified in accounts.yml, it will
              throw an error.
        """
        self.username = username
        self.password = password

    @cached_property
    def user(self):
        u = self.username
        return requests.get("https://api.twitter.com/1/"
                            "users/show.json?screen_name=%s" % u).json()

    def authenticate(self, browser):
        if not self.password:
            self.password = getpass("Please enter the Twitter password "
                                    "for the account %s: " % self.username)
            if self.password == "":
                raise RuntimeError('No password supplied, exiting.')
        browser.open(self.LOGIN_AT)
        browser.form = [f for f in browser.forms()
                        if f.action == "https://twitter.com/sessions"
                        and 'clearfix' in f.attrs['class']][0]

        #   Fill out our form
        browser.form['session[username_or_email]'] = self.username
        browser.form['session[password]'] = self.password
        resp = browser.submit()
        if 'captcha' in resp.geturl():
            raise RuntimeError("Captcha'd. Please log in manually via web.")
        if not '200' in resp._headers.dict['status']:
            raise RuntimeError("Login to %s failed!" % self.__class__.__name__)
        return browser

    def check_name(self):
        return self.user['name']

    def check_location(self):
        return self.user['location']

    def check_biography(self):
        return self.user['description']

    def modify_name(self, value):
        self.modify_profile_attribute('name', value)

    def modify_location(self, value):
        self.modify_profile_attribute('location', value)

    def modify_biography(self, value):
        """
        Modify the twitter bio to match the passed-in value.
        If the bio is too long, raise an exception.
        """
        if len(value) > 160:
            raise ValueError("Twitter bio exceeds maximum length.")
        self.modify_profile_attribute('description', value)

    @invalidates_cache
    @requires_authentication
    def modify_profile_attribute(self, name, value):
        self.browser.open("https://twitter.com/settings/profile")
        self.browser.form = [f for f in self.browser.forms()
                             if f.attrs.get('id', None) == 'profile-form'][0]
        self.browser['user[%s]' % name] = value
        resp = self.browser.submit()
        if resp.code != 200:
            raise RuntimeError("Update failed with a %s error!" % resp.code)

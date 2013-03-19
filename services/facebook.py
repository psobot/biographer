import logging
import requests
import json
from getpass import getpass

from lib.service import Service, requires_authentication,\
                        invalidates_cache, cached_property

log = logging.getLogger(__name__)

#   Fix annoying log output.
logging.getLogger('requests').setLevel(logging.WARNING)


class Facebook(Service):
    LOGIN_AT = 'http://facebook.com'
    USER_ENDPOINT = 'https://graph.facebook.com/cktaylor?access_token=%s'
    EDIT_ENDPOINTS = {
        'name' : '',
        'location' : 'http://m.facebook.com/editprofile.php?edit=current_city&type=basic',
        'website' : 'http://m.facebook.com/editprofile.php?edit=website&type=contact',
        'biography' : 'http://m.facebook.com/editprofile.php?edit=about_me&type=personal'}

    def __init__(self, access_token, username, password=None):
        self.access_token = access_token
        self.username = username
        self.password = password

    # Access tokens from GraphExplorer expire after 2 hours
    # Other than access token though their is no easy way to get full user info without authentication
    @cached_property
    def user(self):
        u = requests.get(self.USER_ENDPOINT % self.access_token).json()
        return u

    def authenticate(self, browser):
        if not self.password:
            self.password = getpass("Please enter the Facebook password "
                                    "for the account %s: " % self.username)
            if self.password == "":
                raise RuntimeError('No password supplied, exiting.')

        browser.set_handle_robots(False)
        resp = browser.open(self.LOGIN_AT)
        form = [f for f in browser.forms()][0]
        form['email'] = self.username
        form['pass'] = self.password
        resp = browser.open(form.click())
        if resp.code != 200:
            raise RuntimeError("Login to %s failed!" % self.__class__.__name__)

        return browser

    def check_name(self):
        print self.user
        return self.user['name']

    def check_location(self):
        return self.user['location']['name']

    def check_website(self):
      return self.user['website']

    def check_biography(self):
        return self.user['bio']

    # There is NO easy way whatsoever to change name, it is not in mobile
    # Perhaps we can go to here without javascript (https://www.facebook.com/settings?tab=account&section=name&view)
    # - we would need to make sure to null out optional settings
    def modify_name(self, value):
        return
        #self.modify_profile_attribute('name', value)

    def modify_location(self, value):
        self.modify_profile_attribute('location', value)

    def modify_website(self, value):
        self.modify_profile_attribute('website', value)

    def modify_biography(self, value):
        self.modify_profile_attribute('biography', value)

    # There was a problem with XHTML being returned, the is_html set might work
    @invalidates_cache
    @requires_authentication
    def modify_profile_attribute(self, name, value):
        resp = self.browser.open(self.EDIT_ENDPOINTS[name])
        print resp.code
        print resp.geturl()
        self.browser.is_html = True
        form = [f for f in self.browser.forms()][0]
        print form
        resp = self.browser.open(form.click())
        if resp.code != 200:
            raise RuntimeError("Update failed with a %s error!" %
                               resp.code)


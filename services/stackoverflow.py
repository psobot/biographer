import time
import logging
import requests
from bs4 import BeautifulSoup
from getpass import getpass

from lib.service import Service, requires_authentication,\
                        invalidates_cache, cached_property

log = logging.getLogger(__name__)

#   Fix annoying log output.
logging.getLogger('requests').setLevel(logging.WARNING)


class StackOverflow(Service):
    LOGIN_AT = "https://openid.stackexchange.com/affiliate/form?affId=4&background=transparent&callback=http%3a%2f%2fstackoverflow.com%2fusers%2fauthenticate&color=black&nonce=ewBFUQAAAABYAQAaNJWBQQ%3d%3d&openid.sreg.requested=email&signupByDefault=false&onLoad=signin-loaded&authCode=bYy0a%2bFdbJAT4qWOeCN0rbEG1g52QNzYcNYGz2JBdGqGX9o2OtZn35ko0IVWyf58jraklkGJ9JDYE1S6niCYqk9C%2fsvW2o%2fn9OQgHSGMd1vKs7msutw%2bNBsJypKJKnPZvU6f2sb%2bGY8YVmBZi799NkG41vpOx%2bGT5o01u60t3Xg%3d"
    USER_ENDPOINT = 'http://api.stackoverflow.com/1.0/users/%s'
    EDIT_ENDPOINT = "http://stackoverflow.com/users/edit/%s"

    # Note: You must have an email address associated through StackExchange OpenID
    # - You also must know the user id associated with your account
    def __init__(self, email, user_id, password=None):
        self.email = email
        self.user_id = user_id
        self.password = password

    # Should work fine. Note: u['biography'] is wrapped in <p> tags for some reason.
    @cached_property
    def user(self):
        resp = requests.get(self.USER_ENDPOINT % self.user_id)
        json_user = resp.json()['users'][0]
        u = {}
        u['name'] = json_user['display_name'].strip()
        u['location'] = json_user['location'].strip()
        u['website'] = json_user['website_url'].strip()
        u['biography'] = json_user['about_me'].strip()
        return u


    # Should work fine. But it seems it sets different cookies then what we want.
    def authenticate(self, browser):
        if not self.password:
            self.password = getpass("Please enter the StackOverflow password "
                                    "for the account %s: " % self.email)
            if self.password == "":
                raise RuntimeError('No password supplied, exiting.')

        browser.set_handle_robots(False)
        resp = browser.open(self.LOGIN_AT)
        form = [f for f in browser.forms()][0]
        form['email'] = self.email
        form['password'] = self.password
        resp = browser.open(form.click())
        bs = BeautifulSoup(resp.read())
        url = bs.find('noscript').find('a')['href']
        resp = browser.open(url)
        if 'AuthFailed' in resp.geturl():
            raise RuntimeError("Login to %s failed!" % self.__class__.__name__)
        return browser

    def check_name(self):
        return self.user['name']

    def check_location(self):
        return self.user['location']

    # There appears to be some discrepencies of the server eating http:// and/or www. prefixes, perhaps make this regex check
    def check_website(self):
        return self.user['website']

    # User object returned on the check is wrapped in <p> tag, so this will need to be smarter
    def check_biography(self):
        return self.user['biography']

    def modify_name(self, value):
        self.modify_profile_attribute('DisplayName', value)

    def modify_location(self, value):
        self.modify_profile_attribute('Location', value)

    def modify_website(self, value):
        self.modify_profile_attribute('WebsiteUrl', value)

    def modify_biography(self, value):
        self.modify_profile_attribute('AboutMe', value)

    # Currently does not work.
    # - The form is obtained correctly, the secret i1l field is grabbed and added correctly
    # - However, the submission results in a 200, when we want a 302
    # - Looks like cookies *may* be at fault
    @invalidates_cache
    @requires_authentication
    def modify_profile_attribute(self, name, value):
        resp = self.browser.open(self.EDIT_ENDPOINT % self.user_id)
        form = [f for f in self.browser.forms()][1]
        timestamp = str(int(time.time() * 1000))
        i1l = self.browser.open('http://stackoverflow.com/questions/ticks?_=%s' % timestamp).read()
        form[name] = value
        form.new_control('hidden', 'i1l', {'value': i1l})
        resp = self.browser.open(form.click())
        if resp.code != 200:
            raise RuntimeError("Update failed with a %s error!" %
                               resp.status_code)


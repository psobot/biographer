# Biographer
### Keep your social info in sync.

---
**How many "social networks" do you have accounts on?** Personally, I've got at least ten. Some of them I visit once a year - some of them every day. Whenever I move, change jobs, or change my bio, I have to update every single one by hand. **That's were Biographer comes in.**

**Biographer** is a little Python app that keeps your info in sync. Fill out `info.yml` like so:

    name: Peter Sobot
    location: San Francisco / Toronto
    biography:
      Musician and software engineering student @uwaterloo.
      
…and `accounts.yml` like so:

    Twitter:
      username: psobot
      
and run:

    python run.py
    
***Et voilà!*** Biographer will check and ensure that your name, location, and bio are all up to date on whatever services you use.

**To get started**, run `pip install -r requirements.txt`, open up your favourite text editor, and edit the `info.yml` and `accounts.yml` files.

---

>*That seems kind of cool. How does it work?*

**Biographer** uses two libraries to do all of its dirty work:

 - [requests](http://docs.python-requests.org/en/latest/) for interacting with simple APIs.
 - [mechanize](https://pypi.python.org/pypi/mechanize/) for browser interaction if some of the data isn't easy to modify via an API.
 
Simply put, **Biographer** tries to talk to an API if possible - but if not, it pretends to be you and updates all of your data exactly as you would through a browser.

>*But won't **Biographer** require my Twitter/Myspace/Friendster password?*

Sometimes. If (and only if) **Biographer** needs to make any changes, it'll prompt you for your password to the required account on the command line. If you're not a fan of password-based auth like that, you're welcome to generate your own OAuth keys for each service and add that (relatively simple) functionality.

>*I'd like to add another service to **Biographer**. How do I do that?*

Easy. Super easy, actually. Add a file called `my_cool_service.py` to `./lib/services/` in this repo. Make sure it contains something like the following:

    import requests
    from lib.service import *  
    
    class MyCoolService(Service):
        def __init__(self, username):
            self.username = username
    
        def authenticate(self, browser):
            self.password = getpass("Please enter the password "
                                    "for the account %s: " % self.username)
            browser.open("http://example.com/login")
            browser.select_form("login_form")
            browser.form['username'] = self.username
            browser.form['password'] = self.password
            browser.submit()
            return browser
    
        def check_biography(self):
            resp = requests.get("http://example.com/" + self.username)
            return resp.json()['biography']
        
        @requires_authentication
        def modify_biography(self, value):
            self.browser.open("https://example.com/settings")
            self.browser.select_form('my_profile')
            self.browser['biography'] = value
            self.browser.submit()
            
Services can be much more complicated than this, and can contain any parameter you want to automate. For example, you could add a `check_favourite_food` method to your service, and add a line like `favourite_food: burritos` to your `info.yml`, and **Biographer** will automatically check to make sure that attribute is up to date. (To *write* to the attribute, you'd also need a `modify_favourite_food` method in your service.)

>*Cool! Should I send you a pull request once I have a new service ready to go?*

**Please do!**

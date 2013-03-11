import yaml
import logging
import inspect
import services
import traceback
from collections import defaultdict
log = logging.getLogger(__name__)


class Enforcer(object):
    """
    The enforcer of consistency.
     - reads data from info.yml and accounts.yml
     - loads services from the services folder
     - runs each service against the provided data to ensure it's up to date
    """

    def __init__(self, info="info.yml", acct="accounts.yml"):
        log.info("Reading info from %s...", info)
        self.data = yaml.load(open(info, 'r'))

        log.info("Reading account info from %s...", acct)
        self.acct = acct
        acct_data = yaml.load(open(acct, 'r'))
        if acct_data:
            self.accounts = dict([(k.lower(), v)
                                for k, v in acct_data.iteritems()])
        else:
            self.accounts = {}

        self.overrides = defaultdict(dict)

        to_delete = []
        for k, v in self.data.iteritems():
            if isinstance(v, dict):
                to_delete.append(k)
                self.overrides[k.lower()] = v
        for k in to_delete:
            del self.data[k]

    def enforce(self):
        for service in self.get_services():
            name =  service.__name__
            try:
                account = self.accounts[name.lower()] or {}
            except KeyError:
                log.error("No account info found for %s. Skipping...", name)
                continue
            try:
                s = service(**account)
            except TypeError as e:
                message = "%s.%s\n" % (name, e.message)
                args, _, _, defaults = inspect.getargspec(service.__init__)
                required_args = args[1:len(args) - len(defaults)]
                message += "Missing required arguments for %s:\n" % name
                for arg in set(required_args) - set(account.keys()):
                    message += "\t%s\n" % arg
                message += "Please add these to %s." % self.acct
                raise Exception(message)
            for k, v in self.data_for(service):
                try:
                    s.ensure(k, v)
                except:
                    log.error("Could not ensure %s for %s!", k, name)
                    log.error(traceback.format_exc())

    def data_for(self, service):
        name = service.__name__.lower()
        for k, v in dict(self.data.items()
                         + self.overrides[name].items()).iteritems():
            yield k, v

    def get_services(self):
        for s in services.__all__:
            module = getattr(services, s)
            for obj in dir(module):
                if obj.lower() == s.lower():
                    yield getattr(module, obj)
                    break

if __name__ == "__main__":
    Enforcer().enforce()

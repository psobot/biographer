import logging
import mechanize
log = logging.getLogger(__name__)


class Service(object):
    """
    The superclass of all services.
    When creating a service, inherit from this class
    and implement the following methods as necessary:
        __init__
        authenticate
        check_<attribute>
        modify_<attribute>
    """

    _authenticated = False
    _cache = {}

    def __init__(self, *args, **kwargs):
        raise NotImplementedError()

    def authenticate(self, *args, **kwargs):
        raise NotImplementedError()

    def ensure(self, key, value):
        name = self.__class__.__name__
        check = getattr(self, "check_" + key.lower(), None)
        modify = getattr(self, "modify_" + key.lower(), None)
        if check and modify:
            log.info("Checking %s on %s...", key, name)
            current = check()
            if current != value:
                log.info("Expected '%s', got '%s'.", value, current)
                log.info("Updating %s on %s...", key, name)
                modify(value)
                current = check()
                if current != value:
                    raise RuntimeError("Value of %s on %s has not changed "
                                       "after modification. Please verify.",
                                       key, name)
                else:
                    log.info("Success! Updated %s on %s.", key, name)
            else:
                log.info("Not modifying %s on %s.", key, name)
        elif check and not modify:
            log.warning("Missing modifier for %s on %s.", key, name)
        elif modify and not check:
            log.warning("Missing checker for %s on %s.", key, name)


def cached_property(fn):
    """
    Decorator that turns the given method into a cached property.
    To clear the cache, delete self._cache[fn].
    The preferred way of clearing the cache is by using an
    "@invalidates_cache" decorator on another method.
    """
    def wrapped(self, *args, **kwargs):
        if fn not in self._cache:
            self._cache[fn] = fn(self, *args, **kwargs)
        return self._cache[fn]
    return property(wrapped)


def invalidates_cache(fn):
    """
    Clears all cached properties after the decorated function is called.
    Useful when changing external (third-party) state that requires
    reverification. (e.g.: decorate a "modify_something" method with this.)
    """
    def wrapped(self, *args, **kwargs):
        r = fn(self, *args, **kwargs)
        self._cache = {}
        return r
    return wrapped


def with_new_browser(fn):
    """
    Forces a new browser object to be created before running the wrapped
    function.
    """
    def wrapped(self, *args, **kwargs):
        self.browser = mechanize.Browser()
        return fn(self, *args, **kwargs)
    return wrapped


def requires_authentication(fn):
    """
    Decorator that forces the "authenticate" method of a service
    to have been called before the given method.
    """
    def wrapped(self, *args, **kwargs):
        if not self._authenticated:
            self.browser = self.authenticate(mechanize.Browser())
            self._authenticated = True
        return fn(self, *args, **kwargs)
    return wrapped

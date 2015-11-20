from calyptos.plugins.validator.validatorplugin import ValidatorPlugin
from urllib2 import Request, urlopen, URLError
import time

class Repos(ValidatorPlugin):
    def validate(self):
        eucalyptus_attributes = self.environment['default_attributes']['eucalyptus']
        self.repotypes = ['default-img-url', 'euca2ools-repo', 'eucalyptus-repo', 'init-script-url', 'post-script-url']
        self.repos = []
        for val in self.repotypes:
            if val in eucalyptus_attributes:
                self.repos.append(eucalyptus_attributes[val])
        retry_delay = 10
        retries = 12
        for url in self.repos:
            req = Request(url)
            for x in range(retries + 1):
                try:
                    response = urlopen(req)
                    self.success('URL: ' + str(url) + ' is valid and reachable!')
                except URLError, e:
                    if x < retries:
                        if hasattr(e, 'reason'):
                            self.warning("Retrying to resolve " + str(url) + " and got: " + str(e.reason))
                        elif hasattr(e, 'code'):
                            self.warning("Retrying to resolve " + str(url) + " and got: " + str(e.code))
                        time.sleep(retry_delay)
                        continue
                    else:
                        if hasattr(e, 'reason'):
                            raise AssertionError("INVALID URL: " + str(url) + "  " + str(e.reason))
                        elif hasattr(e, 'code'):
                            raise AssertionError("INVALID REQUEST: " + str(url) + "  " + str(e.code))
                break

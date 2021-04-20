from . import dbghelp
import time
import os.path
from . import objectpool
from . import config
import re
import logging

logger = logging.getLogger(__name__)

class SymbolServer:
    def __init__(self, globalConfig, serverConfig):
        self._name = config.findConfigValue(serverConfig, "name")
        self._identifier = config.findConfigValue(serverConfig, "identifier", required=True)
        self._remoteURL = config.findConfigValue(serverConfig, "remote", required=True)
        self._cacheLocation = config.findConfigValue(serverConfig, "cacheLocation", default=None)
        self._retryTimeout = config.findConfigValue(serverConfig, "retryTimeout", default=60)
        self._maxRequests = config.findConfigValue(serverConfig, "maxRequests", default=10)
        self._whitelist = config.findConfigValue(serverConfig, "whitelist", default=[".*"])
        self._blacklist = config.findConfigValue(serverConfig, "blacklist", default=[])
        self._previousResults = {}
        self._dbgHelpPool = objectpool.ObjectPool(self._maxRequests, dbghelp.dbghelp, globalConfig.cacheLocation(), self._cacheLocation, self._remoteURL)

        # Generate regex objects for the filtering lists
        self._whitelist = [re.compile(pattern) for pattern in self._whitelist]
        self._blacklist = [re.compile(pattern) for pattern in self._blacklist]

    class SymbolRequestRecord:
        def __init__(self, file, identifier, location):
            self.success = location != None
            self.timestamp = time.time()
            self.location = location
            self.file = file
            self.identifier = identifier

    def filterRequest(self, file):
        # File must match the whitelist
        if not any(regex.match(file) for regex in self._whitelist):
            return False

        # File must not match the blacklist
        if any(regex.match(file) for regex in self._blacklist):
            return False

        return True

    def findFile(self, file, identifier):
        logger.info("{}: find {}/{}".format(self._name, file, identifier))

        # Make sure the request is valid for this server
        if not self.filterRequest(file):
            logger.info("Find ignored - did not match filters")
            return None, True, False

        # Check if the symbol requested has already been requested before
        recordId = file + "/" + identifier
        previousRecord = self._previousResults.get(recordId, None)
        if (previousRecord != None):
            if (previousRecord.success):
                if os.path.exists(previousRecord.location):
                    logger.info("Cache hit - success")
                    return previousRecord.location, True, True
            elif (time.time() - previousRecord.timestamp < self._retryTimeout):
                logger.info("Cache hit - rejection - retry in {}s".format(self._retryTimeout - (time.time() - previousRecord.timestamp)))
                return None, True, True

        # If we made it here then we need to retry the request
        # either because we haven't tried this file,
        # or we've tried before, but the retry timeout has expired
        location = None
        try:
            with objectpool.poolObject(self._dbgHelpPool) as dbgHelp:
                location = dbgHelp.findFile(file, identifier)
        except Exception as e:
            logging.error("{}".format(str(e)))
            pass

        newRecord = self.SymbolRequestRecord(file, identifier, location)
        self._previousResults[recordId] = newRecord
        return newRecord.location, False, True

    def identifer(self):
        return self._identifier

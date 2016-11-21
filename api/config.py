import logging
import logging.config
import logging.handlers
import json
import os

def findConfigFile(candidates):
    for location in candidates:
        if os.path.isfile(location):
            return location
    return candidates[-1]

def findConfigValue(rootDict, name, required = False, default = None):
    curElement = rootDict
    elements = name.split(".")
    for element in elements:
        curElement = curElement.get(element)
        if (curElement == None):
            break

    if (curElement == None):
        if (required):
            raise Exception("Configuration value missing: " + name)
        curElement = default

    return curElement

class Config:
    def __init__(self, configFile):
        # Load configuration information
        self._configFile = configFile
        with open(configFile) as data_file:
            self._configData = json.load(data_file)
        logging.config.dictConfig(self.loggingConfig())

    def configFile(self):
        return self._configFile

    def name(self):
        return self.findConfigValue("identity.name")

    def host(self):
        return self.findConfigValue("identity.host")

    def administrator(self):
        return self.findConfigValue("identity.administrator")

    def sympath(self):
        return self.findConfigValue("identity.default_sympath")

    def servers(self):
        return self.findConfigValue("servers")

    def cacheLocation(self):
        return self.findConfigValue("general.cacheLocation")

    def blacklist(self):
        return self.findConfigValue("general.blacklist")

    def loggingConfig(self):
        return self.findConfigValue("logging", required=False, default={})

    def extractLogFiles(self, logger, logfiles):
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                logfiles.append(handler.baseFilename)
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    for x in range(0, handler.backupCount):
                        logfiles.append(handler.baseFilename + "." + str(x))

    def logfiles(self):
        logfiles = []
        for loggerName in logging.Logger.manager.loggerDict:
            logger = logging.getLogger(loggerName)
            self.extractLogFiles(logger, logfiles)
            self.extractLogFiles(logger.root, logfiles)

        logfiles = list(set(logfiles))
        logfiles = [f for f in logfiles if os.path.exists(f)]
        logfiles.sort()

        return logfiles

    def findConfigValue(self, name, required=True, default=None):
        return findConfigValue(self._configData, name, required, default)



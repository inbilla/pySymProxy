import json
import os
import logging
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('./static'))

logger = logging.getLogger(__name__)

class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if callable(getattr(obj, 'encodeJSON', None)):
            return obj.encodeJSON()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

def getFolderSize(folder):
    if (folder == None):
        return 0

    try:
        total_size = os.path.getsize(folder)
        dirList = os.listdir(folder)
        if dirList == 0:
            return 0

        for item in dirList:
            itempath = os.path.join(folder, item)
            if os.path.isfile(itempath):
                total_size += os.path.getsize(itempath)
            elif os.path.isdir(itempath):
                total_size += getFolderSize(itempath)
        return total_size
    except Exception as e:
        return 0

class MainHandler:
    def __init__(self, config, statistics):
        self._config = config
        self._statistics = statistics
        self._template = env.get_template('main.html.jinja')

    def on_get(self, req, resp, file):
        logging.info("get: {} client: {}".format(file, req.remote_addr))
        try:
            if (file == ""):
                return self.on_get_index(req, resp)
            elif (file == "pysymproxy.json"):
                return self.on_get_config(req, resp)
            elif (file == "statistics.json"):
                return self.on_get_statistics(req, resp)
            elif (file == "symbols.json"):
                return self.on_get_symbols(req, resp)
            elif (file.endswith(".log")):
                return self.on_get_logfile(req, resp, file)
        except Exception as e:
            resp.body = "error: " + str(e)

    def on_get_index(self, req, resp):
        diskUsage = 0  # sum([getFolderSize(server.get("cacheLocation", None)) for server in self._config.servers()])
        diskUsage += getFolderSize(self._config.cacheLocation())
        self._template = env.get_template('main.html.jinja')
        resp.body = self._template.render(
            serverName=self._config.name(),
            admin=self._config.administrator(),
            clientConfig=self._config.sympath(),
            servers=self._config.servers(),
            statistics=self._statistics.getStats(),
            config=self._config._configData,
            diskUsage=diskUsage,
            logfiles=self._config.logfiles()
        )
        resp.content_type = "html"

    def on_get_config(self, req, resp):
        configLocation = self._config.configFile()
        resp.stream = open(configLocation, 'rb')
        resp.stream_len = os.path.getsize(configLocation)
        resp.content_type = "json"

    def on_get_statistics(self, req, resp):
        # Build a dictionary of information to send
        # Serialise it and send
        stats = self._statistics.getStats()
        stats.diskUsage = 0  # sum([getFolderSize(server.get("cacheLocation", None)) for server in self._config.servers()])
        stats.diskUsage += getFolderSize(self._config.cacheLocation())
        stats.numAcceptedRequests = stats.numRequests.value - stats.numExcluded.value

        resp.data = JsonEncoder().encode(stats)
        resp.content_type = "json"

    def on_get_symbols(self, req, resp):
        # Build a dictionary of information to send
        # Serialise it and send
        symbols = self._statistics.getSymbols()

        resp.data = JsonEncoder().encode(symbols)
        resp.content_type = "json"

    def on_get_logfile(self, req, resp, file):
        # Get the list of log files
        logfiles = self._config.logfiles()
        logIndex = int(file[:-4])

        logLocation = logfiles[logIndex - 1]
        resp.stream = open(logLocation, 'rb')
        resp.stream_len = os.path.getsize(logLocation)
        resp.content_type = "text"

import falcon
import os
import re
import symbolserver
import logging
import statistics

logger = logging.getLogger(__name__)

class SymbolHandler:
    def __init__(self, config):
        self._statistics = statistics.Statistics(config)
        self._blacklist = [re.compile(pattern) for pattern in config.blacklist()]

        # build up a list of servers
        self._servers = [symbolserver.SymbolServer(config, serverConfig) for serverConfig in config.servers()]
        self._previousResults = {}

    def getStats(self):
        return self._statistics

    def on_get(self, req, resp, file, identifier, rawfile):
        statRecord = self._statistics.beginRequest(file, identifier)
        symbolLocation = None
        cacheHit = False
        excluded = False
        valid = True
        servers_attempted = []

        try:
            logging.info("get: {}/{}/{} client: {}".format(file, identifier, rawfile, req.remote_addr))

            # Match against list of exclusions
            if file != rawfile:
                valid = False
                raise Exception("Requested file ignored. Compression and file redirection disabled");

            # Match against list of exclusions
            if any(regex.match(file) for regex in self._blacklist):
                excluded = True
                raise Exception("Matched exclusion pattern")

            # Check if we already have a cached record for this request
            recordId = file + "/" + identifier
            previousRecord = self._previousResults.get(recordId, None)
            if previousRecord is not None:
                if previousRecord.success:
                    if os.path.exists(previousRecord.location):
                        logger.info("Cache hit - success")
                        symbolLocation = previousRecord.location
                        cacheHit = True

            if symbolLocation is None:
                # If we made it here then we haven't seen a successful request yet
                # Attempt to find a server that will service this file request
                for server in self._servers:
                    (symbolLocation, cacheHit, lookup_attempted) = server.findFile(file, identifier)

                    if lookup_attempted:
                        servers_attempted.append((server, symbolLocation is not None))

                    if symbolLocation is not None:
                        break

                # No servers attempted to lookup this request
                # so they all must have excluded it individually
                if len(servers_attempted) == 0:
                    excluded = True

            newRecord = symbolserver.SymbolServer.SymbolRequestRecord(file, identifier, symbolLocation)
            self._previousResults[recordId] = newRecord

            if symbolLocation is not None:
                logging.info("response: {}".format(symbolLocation))
                resp.stream = open(symbolLocation, 'rb')
                resp.stream_len = os.path.getsize(symbolLocation)
                resp.content_type = "application/octet-stream"
            else:
                raise Exception("Unable to find file across the servers")

        except Exception, e:
            logging.error("{}".format(str(e)))
            resp.body = "404 could not find requested file.\nError: " + str(e)
            resp.status = falcon.HTTP_404

        self._statistics.endRequest(statRecord, file, identifier, symbolLocation, cacheHit, excluded, valid,
                                    servers_attempted)

from . import requeststatistics
import time


class BlankObject(object):
    def encodeJSON(self):
        result = self.__dict__ .copy()
        del result["symbols"]
        return result

class Statistics:
    def __init__(self, config):
        self._statistics = BlankObject()
        self._statistics.numRequests = requeststatistics.AtomicCounter()
        self._statistics.numInvalidRequests = requeststatistics.AtomicCounter()
        self._statistics.numSuccess = requeststatistics.AtomicCounter()
        self._statistics.numSymbols = requeststatistics.AtomicCounter()
        self._statistics.numCacheHit = requeststatistics.AtomicCounter()
        self._statistics.numPending = requeststatistics.AtomicCounter()
        self._statistics.numExcluded = requeststatistics.AtomicCounter()
        self._statistics.symbols = {}
        self._pending = {}
        self._enabled = config.findConfigValue("general.enableStatistics", required=False, default=True)

    def recordId(self, file, identifier):
        return file

    def beginRequest(self, file, identifier):
        if not self._enabled:
            return

        record = self.recordId(file, identifier)
        stats = self._statistics.symbols.get(record, None)
        if (stats == None):
            stats = requeststatistics.RequestStatistics(file)
            self._statistics.symbols[record] = stats
            self._statistics.numSymbols.increment()

        # Now manipulate the statistics
        self._statistics.numRequests.increment()
        self._statistics.numPending.increment()
        stats.numRequests.increment()
        stats.numPending.increment()

        return (stats, time.time())

    def endRequest(self, statrecord, file, identifier, location, cachehit, exclusion, valid, servers_attempted):
        if not self._enabled:
            return

        stats = statrecord[0]
        stats.numPending.decrement()
        self._statistics.numPending.decrement()

        if not valid:
            self._statistics.numInvalidRequests.increment()
            self._statistics.numRequests.decrement()
            stats.numRequests.decrement()
            return

        beginTime = statrecord[1]
        currentTime = time.time()
        stats.totalTimeServicing.increment(currentTime - beginTime)
        stats.lastAccessTime.assign(currentTime)

        if (location):
            stats.numSuccess.increment()
            self._statistics.numSuccess.increment()
        else:
            stats.numFail.increment()

        if (cachehit):
            stats.numCacheHit.increment()
            self._statistics.numCacheHit.increment()
        else:
            stats.numCacheMiss.increment()

        if (exclusion):
            self._statistics.numExcluded.increment()
            stats.numExcluded.increment()

        for server in servers_attempted:
            if server[1]:
                stats.recordServerHit(server[0])
            else:
                stats.recordServerMiss(server[0])

    def getStats(self):
        if not self._enabled:
            return None

        return self._statistics

    def getSymbols(self):
        if not self._enabled:
            return None

        return self._statistics.symbols

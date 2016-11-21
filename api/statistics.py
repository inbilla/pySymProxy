import requeststatistics
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
        self._statistics.numSuccess = requeststatistics.AtomicCounter()
        self._statistics.numSymbols = requeststatistics.AtomicCounter()
        self._statistics.numCacheHit = requeststatistics.AtomicCounter()
        self._statistics.numPending = requeststatistics.AtomicCounter()
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
        stats.lastAccessTime.assign(time.time())

        return (stats, time.time())

    def endRequest(self, statrecord, file, identifier, location, cachehit):
        if not self._enabled:
            return

        stats = statrecord[0]
        beginTime = statrecord[1]

        stats.totalTimeServicing.increment(time.time()-beginTime)
        stats.numPending.decrement()
        self._statistics.numPending.decrement()

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

    def getStats(self):
        if not self._enabled:
            return None

        return self._statistics

    def getSymbols(self):
        if not self._enabled:
            return None

        return self._statistics.symbols

import threading

class AtomicCounter:
    def __init__(self):
        self.value = 0
        self._lock = threading.Lock()

    def increment(self, amount=1):
        with self._lock:
            self.value += amount

    def decrement(self, amount=1):
        with self._lock:
            self.value -= amount

    def assign(self, value):
        with self._lock:
            self.value = value

    def encodeJSON(self):
        return (self.value)

class RequestStatistics:
    def __init__(self, file):
        self.file = file
        self.totalTimeServicing = AtomicCounter()
        self.numRequests = AtomicCounter()
        self.numSuccess = AtomicCounter()
        self.numFail = AtomicCounter()
        self.numCacheHit = AtomicCounter()
        self.numCacheMiss = AtomicCounter()
        self.numPending = AtomicCounter()
        self.lastAccessTime = AtomicCounter()

    def encodeJSON(self):
        return (self.__dict__)


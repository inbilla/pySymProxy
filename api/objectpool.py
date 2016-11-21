import Queue
from contextlib import contextmanager
import threading

class ObjectPool(object):
    def __init__(self, maxSize, objectType, *args):
        self._semaphore = threading.BoundedSemaphore(maxSize)
        self._queue = Queue.Queue()

        for i in range(0, maxSize):
            self._queue.put(apply(objectType, args))

    def acquire(self):
        self._semaphore.acquire()
        return self._queue.get()

    def release(self, obj):
        self._queue.put(obj)
        self._semaphore.release()

@contextmanager
def poolObject(pool):
    obj = pool.acquire()
    try:
        yield obj
    except Exception, e:
        raise e
    finally:
        pool.release(obj)
# Python 3+ has module "queue", while 2.7 has module "Queue"
try:
    import queue
except ImportError:
    import Queue as queue

from contextlib import contextmanager
import threading

class ObjectPool(object):
    def __init__(self, maxSize, objectType, *args):
        self._semaphore = threading.BoundedSemaphore(maxSize)
        self._queue = queue.Queue()

        for i in range(0, maxSize):
            self._queue.put(objectType(*args))

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
    except Exception as e:
        raise e
    finally:
        pool.release(obj)
from queue import Empty, Full, Queue
from threading import Thread
from typing import Iterable, override


class IterAheadThread[T](Thread):
    """ Wraps an iterable, getting its results in advance and putting them in an internal queue. Good for iterations where getting items is expensive (e.g. internet request), and either response time is important or the items are often retrieved in bursts (e.g. GUI application could be both) (obviously this does not help if the items are consistently requested faster than they can be retrieved).

    Starts itself automatically when iteration begins if not already running. Therefore, note that if you want results to be ready in advance of even the first iteration, you must start the thread explicitly.

    Defaults to `daemon=True` so that shutting it down is optional, but if needed, a `shutdown` method is provided.
    """

    def __init__(self, iterable: Iterable[T], *args, queue_size=5, daemon=True, queue_get_timeout=1., queue_put_timeout=1., **kwargs):
        super().__init__(*args, daemon=daemon, **kwargs)
        self.iterator = iter(iterable)
        self.queue: Queue[T] = Queue(queue_size)
        self.queue_get_timeout = queue_get_timeout
        self.queue_put_timeout = queue_put_timeout
        self.is_shut_down = False
        self.stop_iteration = False

    def __iter__(self):
        return self

    def __next__(self):
        if not self.is_alive():
            if self.stop_iteration:
                raise StopIteration
            self.start()
        try:
            return self.queue.get(timeout=self.queue_get_timeout)
        except Empty:
            if self.stop_iteration:
                raise StopIteration
            else:
                raise

    @override
    def run(self):
        while not self.is_shut_down:
            try:
                next_value = next(self.iterator)
            except StopIteration:
                self.stop_iteration = True
                break

            while not self.is_shut_down:
                try:
                    self.queue.put(next_value, timeout=self.queue_put_timeout)
                except Full:
                    pass
                else:
                    break

    def shutdown(self):
        self.is_shut_down = True
        self.stop_iteration = True


if __name__ == "__main__":
    import time

    def slow_iter():
        for i in range(0, 10):
            yield i
            time.sleep(1)

    t = IterAheadThread(slow_iter())
    t.start()

    time.sleep(10)

    for i in t:
        print(i)

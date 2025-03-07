# (c) Andrew Chen (https://github.com/achen1296)

from abc import ABCMeta, abstractmethod
from queue import Empty, Full, Queue
from threading import Condition, Lock, Thread
from typing import Iterable, Sequence, override

from integers import mod


class IterAheadThread[T](Thread):
    """ Wraps an iterable, getting its results in advance and putting them in an internal queue. Good for iterations where getting items is expensive (e.g. internet request), and either response time is important or the items are often retrieved in bursts (e.g. GUI application could be both) (obviously this does not help if the items are consistently requested faster than they can be retrieved).

    Starts itself automatically when iteration begins if not already running. Therefore, note that if you want results to be ready in advance of even the first iteration, you must start the thread explicitly.

    Defaults to `daemon=True` so that shutting it down is optional, but if needed, a `shutdown` method is provided.
    """

    def __init__(self, iterable: Iterable[T], *thread_args, queue_size=5, queue_get_timeout=1., queue_put_timeout=1., daemon=True, **thread_kwargs):
        super().__init__(*thread_args, daemon=daemon, **thread_kwargs)
        self.iterator = iter(iterable)
        self.queue: Queue[T] = Queue(queue_size)
        self.queue_get_timeout = queue_get_timeout
        self.queue_put_timeout = queue_put_timeout
        self.is_shut_down = False
        self.stop_iteration = False

    def __iter__(self):
        return self

    def __next__(self):
        if not self.is_alive() and not self.stop_iteration:
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


class Loadable[T](metaclass=ABCMeta):
    """ Represents an expensive resource that can be loaded and unloaded. See test code at the bottom of this file for an example implementation. """

    def __init__(self):
        self.loaded = False
        self.loaded_condition = Condition()

    @abstractmethod
    def load(self):
        self.loaded = True
        with self.loaded_condition:
            self.loaded_condition.notify()

    @abstractmethod
    def unload(self):
        self.loaded = False

    @property
    @abstractmethod
    def value_when_loaded(self) -> T:
        pass

    @property
    def value(self):
        while not self.loaded:
            with self.loaded_condition:
                self.loaded_condition.wait()
        return self.value_when_loaded


class LoadWindowThread[T](Thread):
    """ Wraps a `Sequence` (instead of an `Iterable`, to be able to go backwards) of `Loadable` objects (create a subclass). Items up to a certain distance away from the current item will be loaded in advance. Items up to a certain *larger* distance away will be kept, and the rest unloaded. The keep-loaded distance must of course be larger, and should be a reasonable amount larger to account for typical back-and-forth indexing, so that doing so does not unnecessarily unload items that will be reloaded soon. For example, can be used for viewing a list of images back and forth, to load and unload the image data.

    Similar to `IterAheadThread`, starts automatically when any item retrieval method is called, but must be started explicitly to have results prepared in advance of the first call.

    Likewise, by default a `daemon=True` thread with a `shutdown` method. Explicitly calling `shutdown` will unload all resources.

    Does not support iteration directly, as iterators in general only go forward -- in this case `IterAheadThread` is more appropriate.

    Not intended for random access -- works best when index offsets are less than the load distance. Of course, in the case of random access, the only way to guarantee that results are prepared in advance is to load everything anyway. """

    def __init__(self, loadables: Sequence[Loadable[T]], *thread_args, cycle=True, forward_load_distance=5, forward_keep_distance=10, backward_load_distance=5, backward_keep_distance=10, wait_timeout=1., daemon=True, **thread_kwargs):
        if forward_load_distance < 0 or backward_load_distance < 0:
            raise ValueError("load distances must be non-negative")  # might want to keep recent items loaded even without loading in advance, so 0 is allowed
        if forward_keep_distance <= forward_load_distance or backward_keep_distance <= backward_load_distance:
            raise ValueError("unload distances must be greater than load distances")

        super().__init__(*thread_args, daemon=daemon, **thread_kwargs)
        self.loadables = loadables
        self.cycle = cycle
        self.forward_load_distance = forward_load_distance
        self.forward_keep_distance = forward_keep_distance
        self.backward_load_distance = backward_load_distance
        self.backward_keep_distance = backward_keep_distance

        self.wait_timeout = wait_timeout

        self.index = 0

        self.index_changed = False
        self.index_changed_condition = Condition()

        self.is_shut_down = False

    def current(self):
        """ Return the current item without changing the current index. """
        return self.loadables[self.index].value

    def change_index(self, offset: int):
        """ Add `offset` to the index and return that item. Raises `IndexError` if bounds are exceeded, unless cycling. """
        self.index += offset
        ll = len(self.loadables)
        if self.cycle:
            self.index %= len(self.loadables)
        elif self.index < 0 or self.index >= ll:
            self.index = 0
            raise IndexError
        self.index_changed = True
        with self.index_changed_condition:
            self.index_changed_condition.notify()
        return self.loadables[self.index].value

    def previous(self):
        """ Alias for `change_index(-1)."""
        return self.change_index(-1)

    def next(self):
        """ Alias for `change_index(1)."""
        return self.change_index(1)

    @override
    def run(self):
        while not self.is_shut_down:
            ll = len(self.loadables)
            first_keep = self.index - self.backward_keep_distance
            last_keep = self.index + self.forward_keep_distance
            first_load = self.index - self.backward_load_distance
            last_load = self.index + self.forward_load_distance
            for i in range(0, ll):
                if self.is_shut_down:
                    break
                if self.cycle:
                    in_keep_range = mod.in_range(i, first_keep, last_keep, ll)\
                        or self.backward_keep_distance + 1 + self.forward_keep_distance >= ll  # special case for the range being large enough to include everything
                    in_load_range = mod.in_range(i, first_load,  last_load, ll)\
                        or self.backward_load_distance + 1 + self.forward_load_distance >= ll
                else:
                    in_keep_range = first_keep <= i <= last_keep
                    in_load_range = first_load <= i <= last_load
                if not in_keep_range:
                    if self.loadables[i].loaded:
                        self.loadables[i].unload()
                elif in_load_range:
                    if not self.loadables[i].loaded:
                        self.loadables[i].load()

            if self.is_shut_down:
                break

            while not self.is_shut_down and not self.index_changed:
                with self.index_changed_condition:
                    self.index_changed_condition.wait(self.wait_timeout)
            self.index_changed = False

    def shutdown(self):
        self.is_shut_down = True


if __name__ == "__main__":
    import time

    start = time.monotonic()

    def print_with_time(v):
        print(f"{time.monotonic() - start:.2f}: {v}")

    # def slow_iter():
    #     for i in range(0, 10):
    #         yield i
    #         time.sleep(1)

    # t = IterAheadThread(slow_iter(), queue_size=5)
    # t.start()

    # time.sleep(10)

    # # expected result: prints out 0-4 right away having been requested in advance, then the rest slowly
    # for i in t:
    #     print_with_time(i)

    # t.shutdown()
    # t.join()  # verify that shutdown works

    class IntLoadable(Loadable[int]):
        def __init__(self, value: int):
            super().__init__()
            self._value = value

        def load(self):
            time.sleep(1)
            super().load()

        def unload(self):
            super().unload()
            time.sleep(1)

        @property
        def value_when_loaded(self):
            return self._value

    t = LoadWindowThread([IntLoadable(i) for i in range(0, 50)], cycle=True, forward_load_distance=5, forward_keep_distance=10, backward_load_distance=5, backward_keep_distance=10)
    t.start()

    time.sleep(10)

    # should have preloaded 0-5, which print out at once, then 6-11 take 1 second each
    print_with_time(t.current())
    for _ in range(0, 11):
        print_with_time(t.next())

    time.sleep(10)

    # 1-10 should remain loaded and print out instantly, but 0 should have unloaded and need to be loaded again
    print_with_time(t.current())
    for _ in range(0, 11):
        print_with_time(t.previous())

    time.sleep(10)

    # likewise the other way
    print_with_time(t.current())
    for _ in range(0, 11):
        print_with_time(t.previous())

    time.sleep(10)

    print_with_time(t.current())
    for _ in range(0, 11):
        print_with_time(t.next())

    t.shutdown()
    t.join()  # verify that shutdown works

# -*- coding: utf-8 -*-
"""
ThreadPool and Worker classes
"""

__license__ = "MIT License"
__author__ = "Eric Griffin"
__copyright__ = "Copyright (C) 2014, Fluent Trade Technologies"
__version__ = "1.1"


from Queue import Queue
from threading import Thread


class Worker(Thread):
    """Thread executing tasks from a given tasks queue

    :param tasks: The arguments passed which includes the function pointer and its arguments
    """

    def __init__(self, tasks):
        """Class constructor

        :param tasks: The arguments passed which includes the function pointer and its arguments
        """
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        """Run a task from the pool

        """
        while True:
            func, args, kargs = self.tasks.get()
            try:
                func(*args, **kargs)
            except Exception, e:
                print e
            self.tasks.task_done()


class ThreadPool(object):
    """Pool of threads consuming tasks from a queue

    :param num_threads: the number of threads in the pool
    """

    def __init__(self, num_threads):
        """Class constructor

        Creates worker objects
        :param num_threads: the number of threads in the pool
        """
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            Worker(self.tasks)

    def add_task(self, func, *args, **kargs):
        """Add a task to the queue

        Adds a task to the threadpool
        :param func: the function the thread should run
        :param args: function arguments passed to the thread
        :param kargs: key-worded arguments passed to the thread
        """
        self.tasks.put((func, args, kargs))

    def wait_completion(self):
        """Wait for completion of all of the tasks in the queue

        """
        self.tasks.join()
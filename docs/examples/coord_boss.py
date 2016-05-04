#!/usr/bin/env python
#
# Small example demonstrating synchronization.
#
# The boss (this script) simply waits for coord_worker 1 and 2 to both
# send "ready", then sends "Go!" to both of them.
#
# In window 1, type:
# coord_worker.py worker1
#
# In window 2, type:
# coord_worker.py worker2
#
# In window 3, type:
# coord_boss.py
#
# The workers take input and send it to the boss. When the boss
# receives "ready" from both workers, it replies with "GO!".
#
# The workers are really simple. When the boss sends a worker a
# message, the worker echos it. If you type a message into
# a worker, it just sends the message to the boss.
#
# The boss works by setting up a python Event indicating when
# worker1 and worker2 are ready. It then subscribes to
# messages from worker1 and worker2, which simple set the
# corresponding ready Events. Finally, the boss waits for
# both Events to be set, and sends "GO!" to each worker.
# The boss then clears the Events and repeats.

# Compatibility with python3
from __future__ import print_function
from six.moves import input
import six

import sys
import threading
from lcas.Transport import Transport

def main():

    # Create python Events for when worker1 and worker2 are ready.
    ready1 = threading.Event()
    ready2 = threading.Event()

    # These callbacks are called when messages are received from
    # worker1 and worker2. Note that these functions are called
    # in their own thread.

    def check_ready1(tuple):
        if tuple == 'ready':
            print('Worker1 reports ready')
            ready1.set()

    def check_ready2(tuple):
        if tuple == 'ready':
            print('Worker2 reports ready')
            ready2.set()

    # Set up a transport called "boss"
    t = Transport('boss')

    # Listen for messages from workers
    t.subscribe('worker1', check_ready1)
    t.subscribe('worker2', check_ready2)

    # Repeat forever
    while True:

        # Set both workers as not ready.
        ready1.clear()
        ready2.clear()

        print('\nWaiting for workers to be ready')

        # Wait for both workers to have indicated that they're ready.
        # Note that the order doesn't matter. If 2 is ready first, it
        # will remain ready until 1 is also ready.

        ready1.wait()
        ready2.wait()
        
        print('Both workers ready. Telling them to GO!')
        t.send('worker1', 'GO!')
        t.send('worker2', 'GO!')

# main()



if __name__ == "__main__":
    main()

#!/usr/bin/env python
#
# Example of coordinating two workers. The worker simply waits for
# keyboard input, and sends the message to the boss. When the boss
# sends a message, the worker just echos it. See coord_boss.py
# for a more complete explanation.

from __future__ import print_function
from six.moves import input
import six

import sys
from lcas.Transport import Transport

myname = sys.argv[1]

t = Transport(myname)
t.subscribe('boss', lambda tuple: print('Got', tuple, 'from boss'))

while True:
    t.send('boss', input())

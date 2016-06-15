from nluas.Transport import *
# Makes this work with both py2 and py3
from six.moves import input
import sys
from __future__ import print_function

name, destination = sys.argv[1], sys.argv[2]

t = Transport(name)
t.subscribe(destination, lambda ntuple: print("Got", ntuple))

while True:
	t.send(destination, input())



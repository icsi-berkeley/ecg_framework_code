from __future__ import print_function
from nluas.Transport import *
import sys
from six.moves import input

name, destination = sys.argv[1], sys.argv[2]

t = Transport(name)
t.subscribe(destination, lambda ntuple: print("Got", ntuple))

while True:
	t.send(destination, input())



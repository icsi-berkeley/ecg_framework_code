"""
@author: <seantrott@icsi.berkeley.edu

A simple program to output n-tuples using Analyzer+Specializer. Not reliant on any packages other than Jython.


"""

from core_specializer import *
from nluas.ntuple_decoder import *
import traceback
import pprint

decoder = NtupleDecoder()

analyzer = Analyzer("http://localhost:8090")
cs = CoreSpecializer(analyzer)

while True:
    text = input("> ")
    if text == "q":
        quit()
    elif text == "d":
        cs.debug_mode = True
    else:
        try:
            full_parse = analyzer.full_parse(text)
            semspecs = full_parse['parse']
            costs = full_parse['costs']
            for i in range(len(semspecs)):
                try:
                    fs = semspecs[i]
                    cost = costs[i]
                    ntuple = cs.specialize(fs)
                    #decoder.pprint_ntuple(ntuple)
                    #print(ntuple)
                    print("\n")
                    print("SemSpec Cost: {}".format(str(cost)))
                    pprint.pprint(ntuple)
                    break
                except Exception as e:
                    traceback.print_exc()
                    print(e)
        except Exception as e:
            traceback.print_exc()
            print(e)

"""
@author: <seantrott@icsi.berkeley.edu

This will just output a JSON file from input sentences onto ntuples.

"""

from core_specializer import *
from nluas.ntuple_decoder import *
import traceback
import pprint
import sys
import json

decoder = NtupleDecoder()

analyzer = Analyzer("http://localhost:8090")
cs = CoreSpecializer(analyzer)


def convert_parse(parse, observed=[]):
	s = parse
	final = dict()
	for key in parse.__fs__().__dict__.keys():
		new = getattr(s, key)
		#print(repr(new))
		if new.has_filler():
			if new.index() not in observed:
				observed.append(new.index())
				final[key] = convert_parse(new, observed)
		elif new and new.type() != "None":
			final[key] = new.type()
		elif str(new.__value__) != "None":
			#print(new.__value__)
			final[key] = str(new.__value__)

	return final




if __name__ == "__main__":
	maps = dict()
	sentence_file = open(sys.argv[1]) 
	
	sentences = sentence_file.readlines()
	for sentence in sentences:
		try:
			print(sentence)
			full = analyzer.full_parse(sentence)
			semspec = full['parse'][0]
			#parse = convert_parse(semspec, observed=[])
			#print(parse)
			ntuple = cs.specialize(semspec)
			maps[sentence] = dict(ntuple=ntuple,
								  parse=full['original'][0],
								  spans=full['spans'][0])
		except Exception as e:
			print(e)
	output_file = open("generated.json", "w")
	json.dump(maps, output_file)


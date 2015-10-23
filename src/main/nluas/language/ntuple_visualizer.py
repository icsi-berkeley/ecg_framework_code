"""
@author: <seantrott@icsi.berkeley.edu

A simple program to output n-tuples using Analyzer+Specializer. Not reliant on any packages other than Jython.


"""

from core_specializer_alt import *

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
			semspecs = analyzer.parse(text)
			for fs in semspecs:
				try:
					ntuple = cs.specialize(fs)
				except Exception as e:
					print(e)
		except Exception as e:
			print(e)
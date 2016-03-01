from nluas.language.analyzer_proxy import *
import openpyxl
from openpyxl.styles import colors

from graphviz import Digraph

from collections import OrderedDict


def split_sentence(sentence):
	s = sentence.replace(".", " . ").replace(",", " , ")
	return s.split()

def match_spans(split, spans):
	words = OrderedDict()
	for i in range(0, len(split)):
		for span in spans:
			lr = span[0]
			if lr[0] == i and lr[1] == i + 1:
				words[split[i]] = span[1]
	return words

def match_spans2(split, spans):
	final = OrderedDict()
	for span in spans:
		lr = span[0]
		final[span[1]] = (split[lr[0]:lr[1]], lr)
	return final



def tag_excel(matched, split):
	wb = openpyxl.load_workbook('example.xlsx')
	sheet = wb.get_sheet_by_name("Sheet1")
	# Write words to file
	for index in range(len(split)):
		cell = sheet.cell(row=1, column=index+1)
		cell.set_explicit_value(split[index])
	# Write spans
	row = 2
	for key, value in matched.items():
		for j in range(value[1][0], value[1][1]):
			cell = sheet.cell(row=row, column=j+1)
			cell.set_explicit_value(key)
			print("here")
			print(colors.COLOR_INDEX[row])
			#cell.fill = colors.COLOR_INDEX[row]
		row+=1
	wb.save("example.xlsx")
	return sheet

def generate_graph(dot, parse, observed=[], seen=[]):
	
	#s = matched[0]
	s = parse
	last_label = s.__type__
	dot.node(last_label, last_label)
	for key in parse.__fs__().__dict__.keys():
		new = getattr(s, key)

		new_label = str(new.__type__)
		if new_label and new_label != "None":
			dot.node(new_label, new_label)
			dot.edge(last_label, new_label, label=key)
		if new.has_filler() and not new.index() in seen and not new_label in observed and new.__typesystem__ == "SCHEMA":
			print(new_label in observed)
			print(new_label)
			print(observed)
			observed.append(new_label)
			seen.append(new.index())
			g = generate_graph(Digraph(), new, observed, seen)
			dot.subgraph(g)



	return dot


analyzer = Analyzer("http://localhost:8090")


sentence = "he moved the box into the room."
split = split_sentence(sentence)

info = analyzer.full_parse(sentence)
parse, spans = info['parse'], info['spans']

s = match_spans2(split, spans)

dot = Digraph()
graph = generate_graph(dot, parse[0])
#graph.render('label_test/semspec.gv', view=True)


#tag_excel(s, split)









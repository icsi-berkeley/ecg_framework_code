from nluas.language.analyzer_proxy import *
import openpyxl
from openpyxl.styles import colors


analyzer = Analyzer("http://localhost:8090")

from collections import OrderedDict
sentence = "the man ran into the room."
split = sentence.split()

info = analyzer.full_parse(sentence)
parse, spans = info['parse'], info['spans']

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

s = match_spans2(split, spans)

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

tag_excel(s, split)

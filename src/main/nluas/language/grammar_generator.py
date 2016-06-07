"""
For now, outputs a text-file of all the possible words of a given grammar.
Requires that Analyzer is running in a Jython server .

Outputs to framework_code/generated/words.txt
"""

from nluas.language.analyzer_proxy import *
import pprint

analyzer = Analyzer("http://localhost:8090")

lexicon = sorted(list(set(analyzer.get_lexicon())))

#utterances = lexicon = sorted(list(set(analyzer.get_utterances())))


with open("generated/words.txt", "w") as lexicon_file:
	for word in lexicon:
		lexicon_file.write("{}\n".format(word))
	lexicon_file.close()
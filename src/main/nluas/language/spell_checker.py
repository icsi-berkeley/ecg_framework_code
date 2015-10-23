"""
Author: seantrott <seantrott@icsi.berkeley.edu>
"""

import enchant

general = enchant.Dict("en_US")
personal = enchant.pypwl.PyPWL()

import string


# This should be a list of tokens / lexemes available in grammar
tokens = []


# Temporary fill words
fill_words = ["uh", "ah", "um"]

table = dict()

for i in string.punctuation:
    table[ord(i)] = " " + i + " "

#words = original_text.translate(table).split()

class Color(object):
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

class SpellChecker(object):

	def __init__(self, tokens):
		self.general = enchant.Dict("en_US")
		self.personal = enchant.pypwl.PyPWL()
		self.load_tokens(tokens)

	def load_tokens(self, tokens):
		for token in tokens:
			self.personal.add(token)


	def spell_check(self, sentence):
		split = sentence.translate(table).split()
		checked = []
		modified = []
		for word in split:
			if word in fill_words:
				continue
			elif self.personal.check(word):
				checked.append(word)
				modified.append(None)
			else:
				suggestions = self.personal.suggest(word)
				if len(suggestions) > 0:
					suggestion = suggestions[0]
					#checked.append(Color.RED + suggestion + Color.END)
					checked.append(suggestion)
					modified.append(True)
				else:
					return False
		return {'checked': checked, 'modified': modified}
		"""
		corrected = ""
		for word in checked:
			if word in string.punctuation:
				corrected += word
			else:
				corrected += " " + word
		return corrected.strip()
		"""

	def join_checked(self, checked):
		corrected = ""
		for word in checked:
			if word in string.punctuation:
				corrected += word
			else:
				corrected += " " + word
		return corrected.strip()


	def print_modified(self, checked, modified):
		corrected = ""
		index = 0
		while index < len(checked):
			if checked[index] in string.punctuation:
				corrected += checked[index]
			else:
				if modified[index]:
					corrected += " " + Color.RED + checked[index] + Color.END
				else:
					corrected += " " + checked[index]
			index += 1
		return corrected.strip()





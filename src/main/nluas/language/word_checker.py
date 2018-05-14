"""
Combines the features of spell checking and swapping for synonyms with a token.
------
See LICENSE.txt for licensing information.
------
"""

import enchant
import string
import os
import re
import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from nluas.language.spell_checker import Color
from itertools import chain

# mapping between NLTK POS tags and celex morphology types
TAG_DICT = {'JJ':'Positive', 'JJR':'Comparative', 'JJS':'Superlative',
  'NN':'Singular', 'NNS':'Plural', 'NNP':'Singular', 'NNPS':'Plural',
  'RB':'Positive', 'RBR':'Comparative', 'RBS':'Superlative',
  'VB':'Infinitive', 'VBD':'FirstPersonPastTenseSingular',
  'VBG':'ParticiplePresentTense', 'VBN':'ParticiplePastTense',
  'VBP':'FirstPersonPresentTenseSingular', 'VBZ':'PresentTenseSingularThirdPerson'}

class WordChecker(object):

  def __init__(self, prefs_path, lexicon):
    self.general = enchant.Dict("en_US")

    self.morph_files = []
    self.token_files = []
    self.read_prefs(prefs_path)

    self.tokens_in_grammar = set()
    self.tokens_info = dict()
    self.read_tokens()

    self.lemma_to_word = dict()
    self.word_to_lemma = dict()
    self.read_morphs()

    self.lexicon = enchant.pypwl.PyPWL()
    self.load_lexicon(lexicon)

  def read_prefs(self, prefs_path):
    """
      Reads a prefs file and gets the morphology files and token files.
    """
    prefs_folder = "/".join(prefs_path.split("/")[0:-1])
    reading_morphs, reading_tokens = False, False
    with open(prefs_path) as f:
      for line in f:
        line = line.strip()
        if "MORPHOLOGY_PATH ::==" in line:
          reading_morphs = True
        elif "TOKEN_PATH ::==" in line:
          reading_tokens = True
        elif ";" in line:
          reading_morphs, reading_tokens = False, False
        elif reading_morphs == True:
          self.morph_files.append(os.path.join(prefs_folder, line))
        elif reading_tokens == True:
          self.token_files.append(os.path.join(prefs_folder, line))

        if reading_morphs and reading_tokens:
          raise Error("Invalid file")

  def read_tokens(self):
    for token_file in self.token_files:
      with open(token_file) as f:
        for line in f:
          token = line.split('::')[0].strip()
          info = line.split('::')[1:]
          self.tokens_in_grammar.add(token)
          self.tokens_info[token] = info

  def read_morphs(self):
    for morph_file in self.morph_files:
      with open(morph_file) as f:
        for line in f:
          morph = line.split()
          word = morph[0]
          for lemma, tense in zip(morph[1::2], morph[2::2]):
            self.word_to_lemma[word] = lemma
            tense_key = ''.join(sorted(re.split('/|,', tense)))
            if lemma in self.lemma_to_word:
              self.lemma_to_word[lemma][tense_key] = word
            else:
              self.lemma_to_word[lemma] = {tense_key : word}

  def load_lexicon(self, lexicon):
    for word in lexicon:
      self.lexicon.add(word)

  def check(self, sentence):
    tagged_words = nltk.pos_tag(nltk.word_tokenize(sentence))
    checked, modified, failed = [], [], []
    for i in range(len(tagged_words)):
      checked_word, is_modified = self.check_word(i, tagged_words)
      if is_modified is None:
        failed.append(True)
      else:
        failed.append(False)
      checked.append(checked_word)
      modified.append(bool(is_modified))
    return {'checked': checked, 'modified': modified, 'failed': failed}

  def check_word(self, i, tagged_words):
    word, pos_tag = tagged_words[i]
    if self.lexicon.check(word) or word in string.punctuation:
      return word, False
    if i+1 < len(tagged_words) and self.lexicon.check("{}_{}".format(word, tagged_words[i+1][0])):
      return word, False
    if i-1 >= 0 and self.lexicon.check("{}_{}".format(tagged_words[i-1][0], word)):
      return word, False
    if self.general.check(word):
      synonym = self.get_synonym(word, pos_tag)
      if synonym:
        return synonym, True

    try:
      int(word)
      return word, False
    except:
      pass

    lexicon_suggestions = self.lexicon.suggest(word)
    if len(lexicon_suggestions) > 0:
      return lexicon_suggestions[0], True

    general_suggestions = self.general.suggest(word)
    if len(general_suggestions) > 0:
      for suggestion in general_suggestions:
        synonym = self.get_synonym(suggestion, pos_tag)
        if synonym:
          return synonym, True

    if self.general.check(word):
      synonym = self.get_synonym(word, None)
      if synonym:
        return synonym, True

    return word, None

  def get_synonym(self, word, pos_tag):
    if pos_tag:
      tense = TAG_DICT[pos_tag] if pos_tag in TAG_DICT else 'NoMorphology'
      pos = self.penn_to_wn(pos_tag)

      if pos is None:
        return None

      wnl = WordNetLemmatizer()
      # # https://stackoverflow.com/questions/19258652/how-to-get-synonyms-from-nltk-wordnet-python
      lemma = wnl.lemmatize(word, pos=pos)
    else:
      lemma = word

    synonym_synsets = wordnet.synsets(lemma)
    synonyms = set(chain.from_iterable([s.lemma_names() for s in synonym_synsets]))

    valid = []
    for synonym in synonyms:
      if synonym in self.tokens_in_grammar:
        if tense in self.lemma_to_word[synonym]:
          if self.lexicon.check(self.lemma_to_word[synonym][tense]):
               valid.append(self.lemma_to_word[synonym][tense])
    return valid[0] if len(valid) > 0 else None

  # Source: https://stackoverflow.com/questions/27591621/nltk-convert-tokenized-sentence-to-synset-format
  def penn_to_wn(self, tag):
    if not tag:
      return None
    elif tag.startswith('J'):
      return wordnet.ADJ
    elif tag.startswith('N'):
      return wordnet.NOUN
    elif tag.startswith('R'):
      return wordnet.ADV
    elif tag.startswith('V'):
      return wordnet.VERB
    return None

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

  def get_failed(self, table):
    checked, failed = table['checked'], table['failed']
    failures = []
    for word, is_fail in zip(checked, failed):
      if is_fail:
        failures.append(word)
    return failures

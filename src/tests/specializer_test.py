"""
author: <seantrott@icsi.berkeley.edu>

Tests CoreSpecializer (currently core_specializer.py) against a JSON struct of sentences/n-tuples.
Requires the Jython analyzer to be running.

Intended to run with "research.prefs"

"""

from nluas.language.core_specializer import *
import json
import unittest
from json import loads, dumps

analyzer = Analyzer("http://localhost:8090")
specializer = CoreSpecializer(analyzer)

sentences = ["boxes are big.",
             "he moved.",
             "the box is big.",
             "he pushed the box.",
             "he pushed the box into the room.",
             "he saw the block.",
             "he sprinted into the room.",
             "he moved the box 3 inches.",
             "the box costs 3 pounds.",
             "the box weighs 3 pounds.",
             "he painted the room blue.",
             "he made the box bigger."]

def generate_ntuple(sentence):
    try:
        semspecs = analyzer.parse(sentence)
        for semspec in semspecs:
            ntuple = specializer.specialize(semspec)
            break
    except Exception as e:
        print(e)
    return ntuple

def generate_ntuples(sentences):
    ntuples = {}
    for sentence in sentences:
        ntuple = generate_ntuple(sentence)
        ntuples[sentence] = ntuple
    return ntuples

def to_dict(ntuple):
    return loads(dumps(ntuple))

def write_file(sentences):
    ntuples = generate_ntuples(sentences)
    with open("src/tests/ntuple_tests.json", "w") as f:
        json.dump(ntuples, f)



class SpecializerTests(unittest.TestCase):

    def setUp(self):
        #self.sentence = None
        self.maxDiff = None
        with open("src/tests/ntuple_tests.json", "r") as file:
            self.ntuple_tests = json.load(file)

    def test_batch(self):
        for sentence in sentences:
            self.sentence = sentence
            self.evaluate_output(sentence)

    def evaluate_output(self, sentence):
        print("Evaluating '{}'...".format(sentence))
        ntuple = generate_ntuple(sentence)
        self.assertEqual(ntuple, self.ntuple_tests[sentence])


if __name__ == "__main__":
    #write_file(sentences)
    unittest.main()










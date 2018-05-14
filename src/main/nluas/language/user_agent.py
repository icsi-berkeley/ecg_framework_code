
"""
The User-Agent (also called UI-Agent, Agent-UI) receives text/speech
as input, and produces an n-tuple, which it sends to a ProblemSolver.
It feeds the text through the ECG Analyzer (running on a local server)
to produce a SemSpec, which it then runs through the CoreSpecializer to produce
the n-tuple.

Interaction with the user is modulated through the output_stream method, which
allows designers to subclass the User-Agent and define a new mode of interaction.


Author: seantrott <seantrott@icsi.berkeley.edu>


------
See LICENSE.txt for licensing information.
------

"""

from nluas.language.core_specializer import *
from nluas.language.word_checker import WordChecker
from nluas.core_agent import *
from nluas.language.analyzer_proxy import *
from nluas.ntuple_decoder import NtupleDecoder
import sys, traceback, time
import json
import time
from collections import OrderedDict

# Makes this work with both py2 and py3
from six.moves import input

class UserAgent(CoreAgent):
    def __init__(self, args):
        """args are execpted to be a prefs_path followed by the CoreAgent args"""
        self.prefs_path = args[0]
        CoreAgent.__init__(self, args[1:])
        self.initialize_UI()
        self.solve_destination = "{}_{}".format(self.federation, "ProblemSolver")
        self.speech_address = "{}_{}".format(self.federation, "SpeechAgent")
        self.text_address = "{}_{}".format(self.federation, "TextAgent")
        self.transport.subscribe(self.solve_destination, self.callback)
        self.transport.subscribe(self.speech_address, self.speech_callback)
        self.transport.subscribe(self.text_address, self.text_callback)

    def setup_ui_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-port", type=str, help="indicate host to connect to",
                            default="http://localhost:8090")
        return parser

    def initialize_UI(self):
        self.clarification = False
        self.analyzer_port = "http://localhost:8090"
        connected, printed = False, False
        while not connected:
            try:
                self.initialize_analyzer()
                self.initialize_specializer()
                self.initialize_wordchecker()
                connected = True
            except ConnectionRefusedError as e:
                if not printed:
                    message = "The analyzer_port address provided refused a connection: {}".format(self.analyzer_port)
                    self.output_stream(self.name, message)
                    printed = True
                time.sleep(1)

        self.decoder = NtupleDecoder()

    def initialize_analyzer(self):
        self.analyzer = Analyzer(self.analyzer_port)

    def initialize_specializer(self):
        try:
            self.specializer=CoreSpecializer(self.analyzer)
        except TemplateException as e:
            self.output_stream(self.name, e.message)
            self.transport.quit_federation()
            quit()

    def initialize_wordchecker(self):
        self.word_checker = WordChecker(self.prefs_path, self.analyzer.get_lexicon())

    def match_spans(self, spans, sentence):
        sentence = sentence.replace(".", " . ").replace(",", " , ").replace("?", " ? ").replace("!", " ! ").split()
        final = []
        for span in spans:
            lr = span['span']
            final.append([span['type'], sentence[lr[0]:lr[1]], lr, span['id']])
        return final

    def process_input(self, msg):
        try:
            table = self.word_checker.check(msg)
            if any(table['failed']):
                failures = self.word_checker.get_failed(table)
                raise Exception("Unknown tokens in inputs: {}".format(failures))

            msg = self.word_checker.join_checked(table['checked'])
            full_parse = self.analyzer.full_parse(msg)
            semspecs = full_parse['parse']
            spans = full_parse['spans']
            index = 0
            for fs in semspecs:
                try:
                    span = spans[index]
                    matched = self.match_spans(span, msg)
                    self.specializer.set_spans(matched)
                    ntuple = self.specializer.specialize(fs)
                    return ntuple
                except Exception as e:
                    if self.verbose:
                        traceback.print_exc()
                        self.output_stream(self.name, e)
                    index += 1
        except Exception as e:
            print(e)

    def output_stream(self, tag, message):
        print("{}: {}".format(tag, message))


    def speech_callback(self, ntuple):
        """ Processes text from a SpeechAgent. """
        text = ntuple['text'].lower()
        if self.verbose:
            print("Got {}".format(text))
        new_ntuple = self.process_input(text)
        if new_ntuple and new_ntuple != "null" and "predicate_type" in new_ntuple:
            self.transport.send(self.solve_destination, new_ntuple)


    def text_callback(self, ntuple):
        """ Processes text from a SpeechAgent. """
        specialize = True
        msg = ntuple['text']
        if self.is_quit(ntuple):
            self.close()
        elif ntuple['type'] == "standard":
            if msg == None or msg == "":
                specialize = False
            elif msg.lower() == "d":
                self.specializer.set_debug()
                specialize = False
            elif specialize:
                new_ntuple = self.process_input(ntuple['text'])
                if new_ntuple and new_ntuple != "null" and "predicate_type" in new_ntuple:
                    self.transport.send(self.solve_destination, new_ntuple)
        elif ntuple['type'] == "clarification":
            descriptor = self.process_input(msg)
            self.clarification = False
            new_ntuple = self.clarify_ntuple(ntuple['original'], descriptor)
            self.transport.send(self.solve_destination, new_ntuple)
            self.clarification = False


    def callback(self, ntuple):
        call_type = ntuple['type']
        if call_type == "id_failure":
            self.output_stream(ntuple['tag'], ntuple['message'])
        elif call_type == "clarification":
            self.process_clarification(ntuple['tag'], ntuple['message'], ntuple['ntuple'])
        elif call_type == "response":
            self.output_stream(ntuple['tag'], ntuple['message'])
        elif call_type == "error_descriptor":
            self.output_stream(ntuple['tag'], ntuple['message'])

    def write_file(self, json_ntuple, msg):
        sentence = msg.replace(" ", "_").replace(",", "").replace("!", "").replace("?", "")
        t = str(time.time())
        generated = "src/main/json_tuples/" + sentence
        f = open(generated, "w")
        f.write(json_ntuple)

    def process_clarification(self, tag, msg, ntuple):
        self.clarification = True
        if self.verbose:
            self.output_stream(tag, msg)
        new_ntuple = {'tag': tag, 'message': msg, 'type': "clarification", 'original': ntuple}
        self.transport.send(self.text_address, new_ntuple)

    def clarify_ntuple(self, ntuple, descriptor):
        """ Clarifies a tagged ntuple with new descriptor. """
        new = dict()
        for key, value in ntuple.items():
            if "*" in key:
                new_key = key.replace("*", "")
                new[new_key] = descriptor
            elif type(value) == dict:
                new[key] = self.clarify_ntuple(value, descriptor)
            else:
                new[key] = value
        return new

if __name__ == "__main__":
    ui = UserAgent(sys.argv[1:])


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
from nluas.core_agent import *
from nluas.language.analyzer_proxy import *
from nluas.ntuple_decoder import NtupleDecoder
#from nluas.language.spell_checker import *
import sys, traceback, time
import json
import time
from collections import OrderedDict

# Kind of hacky, but it should make this work with both Python2 and Python3.
try:
    input = raw_input
except NameError as e:
    #print("We're running Python3, so we're already good.")
    pass

class WaitingException(Exception):
    def __init__(self, message):
        self.message = message

class UserAgent(CoreAgent):
    def __init__(self, args):
        #self.ui_parser = self.setup_ui_parser()


        CoreAgent.__init__(self, args)
        self.initialize_UI()
        #self.ui_parser = self.setup_ui_parser()
        #self.analyzer_port = self.unknown[0]
        self.solve_destination = "{}_{}".format(self.federation, "ProblemSolver")
        self.transport.subscribe(self.solve_destination, self.callback)


    def setup_ui_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-port", type=str, help="indicate host to connect to",
                            default="http://localhost:8090")
        return parser

    def initialize_UI(self):
        #args = self.ui_parser.parse_known_args(self.unknown)
        #self.analyzer_port = args[0].port
        self.clarification = False
        self.analyzer_port = "http://localhost:8090"
        connected, printed = False, False
        while not connected:
            try:
                self.initialize_analyzer()
                connected = True
            except ConnectionRefusedError as e:
                if not printed:
                    message = "The analyzer_port address provided refused a connection: {}".format(self.analyzer_port)
                    self.output_stream(self.name, message)
                    printed = True
                time.sleep(1)
            try:
                self.initialize_specializer()
            except TemplateException as e:
                self.output_stream(self.name, e.message)
                self.transport.quit_federation()
                quit()
        self.decoder = NtupleDecoder()
        #self.spell_checker = SpellChecker(self.analyzer.get_lexicon())

    def initialize_analyzer(self):
        self.analyzer = Analyzer(self.analyzer_port)
        
    def initialize_specializer(self):
        self.specializer=CoreSpecializer(self.analyzer)

    def match_spans(self, spans, sentence):
        sentence = sentence.replace(".", " . ").replace(",", " , ").replace("!", " ! ").split(" ")
        final = OrderedDict()
        for span in spans:
            lr = span['span']
            final[span['type']] = (sentence[lr[0]:lr[1]], lr, span['id'])
        return final

    def process_input(self, msg):
        try:
            full_parse = self.analyzer.full_parse(msg)
            semspecs = full_parse['parse']
            spans = full_parse['spans']
            
            #semspecs = self.analyzer.parse(msg)
            index = 0
            for fs in semspecs:
                try:
                    span = spans[index]
                    matched = self.match_spans(span, msg)
                    self.specializer.set_spans(matched)
                    ntuple = self.specializer.specialize(fs)

                    json_ntuple = self.decoder.convert_to_JSON(ntuple)
                    return json_ntuple
                except Exception as e:
                    self.output_stream(self.name, e)
                    #traceback.print_exc()
                    index += 1
        except Exception as e:
            print(e)

    def output_stream(self, tag, message):
        # Should actually just print to self._out
        print("{}: {}".format(tag, message))

    def callback(self, ntuple):
        ntuple = self.decoder.convert_JSON_to_ntuple(ntuple)
        call_type = ntuple['type']
        if call_type == "id_failure":
            self.output_stream(ntuple['tag'], ntuple['message'])
            #print(ntuple['message'])
        elif call_type == "clarification":
            #self.output_stream("{}: {}".format(ntuple['tag'], ntuple['message']))
            #self.prompt(clarification=True, ntuple=ntuple['ntuple'])
            #self.output_stream(ntuple['tag'], ntuple)
            self.process_clarification(ntuple['tag'], ntuple['message'], ntuple['ntuple'])
            #print(ntuple['ntuple'])
        elif call_type == "response":
            self.output_stream(ntuple['tag'], ntuple['message'])
        elif call_type == "error_descriptor":
            self.output_stream(ntuple['tag'], ntuple['message'])
        #print(ntuple)
        #decoded = self.decoder.convert_JSON_to_ntuple(ntuple)
        #print(decoded)

    def write_file(self, json_ntuple, msg):
        sentence = msg.replace(" ", "_").replace(",", "").replace("!", "").replace("?", "")
        t = str(time.time())
        generated = "src/main/json_tuples/" + sentence
        f = open(generated, "w")
        f.write(json_ntuple)

    def prompt(self):
        while True:# and not self.clarification:
            #print(self.clarification)
            if self.clarification:
                pass
            else:
                specialize = True
                msg = input("> ")

                if msg == "q":
                    self.transport.quit_federation()
                    quit()
                elif msg == None or msg == "":
                    specialize = False
                elif msg.lower() == 'd':
                    self.specializer.set_debug()
                    specialize = False
                elif specialize:
                    #if self.check_spelling(msg):
                    json_ntuple = self.process_input(msg)
                    if json_ntuple and json_ntuple != "null" and "predicate_type" in json.loads(json_ntuple):
                        self.transport.send(self.solve_destination, json_ntuple)



    def process_clarification(self, tag, msg, ntuple):
        self.clarification = True
        self.output_stream(tag, msg)
        #print(ntuple)
        while True:
            msg = input("  > ")
            #if msg == "q":
            #    self.clarification = False
            #    self.transport.quit_federation()
            if msg == "q":
                self.clarification = False
                break
            elif msg:
                try:
                    first = self.process_input(msg)
                    descriptor = json.loads(first)
                    #print(descriptor)
                    converted = self.decoder.convert_JSON_to_ntuple(ntuple)
                    self.clarification = False
                    new_ntuple = self.clarify_ntuple(converted, descriptor)
                    json_ntuple = self.decoder.convert_to_JSON(new_ntuple)
                    #json_ntuple = json.dumps(new_ntuple)
                    self.transport.send(self.solve_destination, json_ntuple)
                    self.clarification = False
                    break
                except Exception as e:
                    print(e)


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

    
    def check_spelling(self, msg):
        table = self.spell_checker.spell_check(msg)
        if table:
            checked =self.spell_checker.join_checked(table['checked'])
            if checked != msg:
                print(self.spell_checker.print_modified(table['checked'], table['modified']))
                affirm = input("Is this what you meant? (y/n) > ")
                if affirm and affirm[0].lower() == "y":
                    self.process_input(checked)
                else:
                    return
            else:
                self.process_input(msg)


if __name__ == "__main__":
    ui = UserAgent(sys.argv[1:])
    ui.prompt()



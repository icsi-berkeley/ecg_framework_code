"""
Author: seantrott <seantrott@icsi.berkeley.edu>

"""

from nluas.language.core_specializer import *
from nluas.core_agent import *
from nluas.language.analyzer_proxy import *
from nluas.ntuple_decoder import NtupleDecoder
#from nluas.language.spell_checker import *
import sys, traceback, time
import json

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
        self.analyzer_port = "http://localhost:8090"
        connected, printed = False, False
        while not connected:
            try:
                self.initialize_analyzer()
                self.initialize_specializer()
                connected = True
            except Exception as e:
                if not printed:
                    message = "The analyzer_port address provided refused a connection: {}".format(self.analyzer_port)
                    self.output_stream(self.name, message)
                    printed = True
                time.sleep(1)
        self.decoder = NtupleDecoder()
        #self.spell_checker = SpellChecker(self.analyzer.get_lexicon())

    def initialize_analyzer(self):
        self.analyzer = Analyzer(self.analyzer_port)
        
    def initialize_specializer(self):
        self.specializer=CoreSpecializer(self.analyzer)

    def process_input(self, msg):
        try:
            semspecs = self.analyzer.parse(msg)
            for fs in semspecs:
                try:
                    ntuple = self.specializer.specialize(fs)
                    json_ntuple = self.decoder.convert_to_JSON(ntuple)
                    #if self.specializer.debug_mode:
                    #   self.write_file(json_ntuple, msg)
                    self.transport.send(self.solve_destination, json_ntuple)
                    break
                except Exception as e:
                    self.output_stream(self.name, e)
                    traceback.print_exc()
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
        while True:
            specialize = True
            msg = raw_input("> ")
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
                self.process_input(msg)



    def process_clarification(self, tag, msg, ntuple):
        self.output_stream(tag, msg)
        #msg = input(msg + "> ")
        new = self.decoder.convert_JSON_to_ntuple(ntuple)
        #print(new)
        #print(msg)
        #print(ntuple)

    
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



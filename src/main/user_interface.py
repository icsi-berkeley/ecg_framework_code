from nluas.core_solver import CoreProblemSolver
from nluas.core_specializer import *
import sys, traceback
from nluas.ntuple_decoder import NtupleDecoder
from nluas.analyzer_proxy import Analyzer
from nluas.spell_checker import SpellChecker
try:
    # Python 2?
    from xmlrpclib import ServerProxy, Fault  # @UnresolvedImport @UnusedImport
except:
    # Therefore it must be Python 3.
    from xmlrpc.client import ServerProxy, Fault


class UserInterface(object):
    #def __init__(self):

    def prompt(self):
        while True:
            ans = input("Press q/Q to quit, d/D for Debug mode> ")
            specialize = True
            if ans == None or ans == "":
                specialize = False
            elif ans.lower()[0] == 'd':
                specializer._output = handle_debug()
                specialize = False
            elif ans.lower()[0] == 'q':
                solver.close()
                quit()
            elif ans and specialize:
                table = spellChecker.spell_check(ans)
                if table:
                    checked =spellChecker.join_checked(table['checked'])
                    if checked != ans:
                        print(spellChecker.print_modified(table['checked'], table['modified']))
                        affirm = input("Is this what you meant? (y/n) > ")
                        if affirm[0].lower() == "y":
                            ans = checked
                        else:
                            specialize = False
                    if specialize:
                        specializer._sentence = ans
                        try:
                            return analyzer.parse(ans)
                        except Fault as err:
                            print('Fault', err)
                            if err.faultString == 'compling.parser.ParserException':
                                print("No parses found for '%s'" % ans)



    def solve_loop(self, prompted):
        count = 1
        for fs in prompted:
            try:
                ntuple = specializer.specialize(fs)
                json_ntuple = transporter.convert_to_JSON(ntuple)
                #try:
                solver.solve(json_ntuple)
                break
            except Exception as e:
                print("Problem solving SemSpec #{}".format(count))
                count += 1
                print(e)
                #traceback.print_exc(limit=1)

    def main_loop(self):
        while True:
            result = self.prompt()
            self.solve_loop(result)

    def clarify(self, ntuple, message, name):
        print("{}: {}".format(name, message))
        #self.main_loop
        return None


analyzer = Analyzer('http://localhost:8090')
specializer = CoreSpecializer()
transporter = NtupleDecoder()

spellChecker = SpellChecker(analyzer.get_lexicon())

interface = UserInterface()
solver = CoreProblemSolver(interface.clarify)


interface.main_loop()

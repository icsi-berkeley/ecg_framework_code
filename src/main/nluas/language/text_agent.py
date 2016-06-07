
"""
The Text-Agent prompts a user for input, then sends the input to the UserAgent.

Interaction TBD.


Author: seantrott <seantrott@icsi.berkeley.edu>


------
See LICENSE.txt for licensing information.
------

"""

from nluas.core_agent import *
import json
#from nluas.language.spell_checker import *

# Makes this work with both py2 and py3
from six.moves import input

class WaitingException(Exception):
    def __init__(self, message):
        self.message = message

class TextAgent(CoreAgent):
    def __init__(self, args):
        CoreAgent.__init__(self, args)
        self.clarification = False
        self.ui_destination = "{}_{}".format(self.federation, "AgentUI")
        self.transport.subscribe(self.ui_destination, self.callback)
        self.original = None

    def prompt(self):
        #if not self.clarification:
        #print("Calling prompt....")
        #print("Clarification is: {}".format(self.clarification))
        msg = input("> ")
        if msg == "q":
            self.transport.quit_federation()
            quit()
        elif msg == None or msg =="":
            pass
        else:
            if self.clarification:
                ntuple = {'text': msg, 'type': "clarification", 'original': self.original}
                self.clarification = False
            else:
                ntuple = {'text': msg, 'type': "standard"}
            self.transport.send(self.ui_destination, ntuple)

    def callback(self, ntuple):
        """ Callback for receiving information from UI-Agent. """
        #ntuple = json.loads(ntuple)
        if "type" in ntuple and ntuple['type'] == "clarification":
            self.clarification = True
            self.original = ntuple['original']
            self.output_stream(ntuple['tag'], ntuple['message'])



    def output_stream(self, tag, message):
        print("{}: {}".format(tag, message))


if __name__ == "__main__":
    text = TextAgent(sys.argv[1:])
    while True:
        text.prompt()
        
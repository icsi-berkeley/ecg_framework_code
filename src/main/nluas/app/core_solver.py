"""
Simple solver "core". Contains capabilities for unpacking 
a JSON n-tuple, as well as routing this n-tuple based 
on the predicate_type (command, query, assertion, etc.). 
Other general capabilities can be added. The design 
is general enough that the same "unpacking" and "routing" 
method can be used, as long as a new method is written for a given
predicate_type. 

"Route_action" can be called by command/query/assertion methods,
to route each parameter to the task-specific method. E.g., "solve_move",
or "solve_push_move", etc.

Author: seantrott <seantrott@icsi.berkeley.edu>



"check_for_clarification" should check ntuple and determine if everything is
specified enough. This implementation will depend on a solver's world model,
but the schematic implementation can be implemented here.

"""

from nluas.ntuple_decoder import *
from nluas.core_agent import *
import random
import sys, traceback
import json

def check_complexity(n):
    s = int(n)
    if s not in [1, 2, 3]:
        raise argparse.ArgumentTypeError("{} is an invalid entry for the complexity level. Should be 1, 2, or 3.".format(n))
    return s

class CoreProblemSolver(CoreAgent):

    def __init__(self, args):
        self.ntuple = None
        self.decoder = NtupleDecoder()
        CoreAgent.__init__(self, args)
        self.world = []
        self.solver_parser = self.setup_solver_parser()
        args = self.solver_parser.parse_args(self.unknown)
        self.complexity = args.complexity
        self.ui_address = "{}_{}".format(self.federation, "AgentUI")
        self.transport.subscribe(self.ui_address, self.callback)
        self._incapable = "I cannot do that yet."
        self.history = list()

    def setup_solver_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-c", "--complexity", default=1, type=check_complexity, help="indicate level of complexity: 1, 2, or 3.")
        return parser

    def callback(self, ntuple):
        self.solve(ntuple)

    def request_clarification(self, ntuple, message="This ntuple requires clarification."):
        new = self.decoder.convert_to_JSON(ntuple)
        request = {'ntuple': new, 'message': message, 'type': 'clarification', 'tag': self.address}
        self.transport.send(self.ui_address, json.dumps(request))

    def identification_failure(self, message):
        request = {'type': 'failure', 'message': message, 'tag': self.address}
        self.transport.send(self.ui_address, json.dumps(request))

    def respond_to_query(self, message):
        request = {'type': 'response', 'message': message, 'tag': self.address}
        self.transport.send(self.ui_address, json.dumps(request))

    def solve(self, json_ntuple):
        ntuple = self.decoder.convert_JSON_to_ntuple(json_ntuple)
        if self.check_for_clarification(ntuple):
            self.request_clarification(ntuple=ntuple)
        else:
            self.ntuple = ntuple
            predicate_type = ntuple['predicate_type']
            try:
                dispatch = getattr(self, "solve_%s" %predicate_type)
                dispatch(ntuple)
                self.broadcast()
            except AttributeError as e:
                traceback.print_exc()
                message = "I cannot solve a(n) {}.".format(predicate_type)
                self.identification_failure(message)

    def broadcast(self):
        """ Here, does nothing. Later, an AgentSolver will broadcast information back to BossSolver. """
        pass
                
    def update_world(self, discovered=[]):
        for item in discovered:
            self.world.append(item)

    def solve_command(self, ntuple):
        self.decoder.pprint_ntuple(ntuple)

    def solve_query(self, ntuple):
        self.decoder.pprint_ntuple(ntuple)

    def solve_assertion(self, ntuple):
        self.decoder.pprint_ntuple(ntuple)

    def solve_conditional_imperative(self, ntuple):
        self.decoder.pprint_ntuple(ntuple)

    def solve_conditional_declarative(self, ntuple):
        self.decoder.pprint_ntuple(ntuple)

    def route_event(self, eventDescription, predicate):
        features = eventDescription['e_features']
        if features:
            efeatures = features['eventFeatures']
        parameters = eventDescription['eventProcess']
        self.route_action(parameters, predicate)


    def route_action(self, parameters, predicate):
        if "complexKind" in parameters and parameters['complexKind'] == "serial":
            self.solve_serial(parameters, predicate)
        else:
            action = parameters['actionary']
            try:
                dispatch = getattr(self, "{}_{}".format(predicate, action))
                dispatch(parameters)
                self.history.insert(0, (parameters, True))
            except AttributeError as e:
                traceback.print_exc()
                message = "I cannot solve the '{}_{}' action".format(predicate,action)
                self.history.insert(0, (parameters, False))
                self.identification_failure(message)

    def close(self):
        return

    def solve_serial(self, parameters):
        print(parameters)

    def check_for_clarification(self, ntuple):
        """ Will need to be replaced by a process that checks whether ntuple needs clarification.
        Requires some sort of context/world model. """
        #return random.choice([True, False])
        return False

if __name__ == '__main__':
    ps = CoreProblemSolver(sys.argv[1:])

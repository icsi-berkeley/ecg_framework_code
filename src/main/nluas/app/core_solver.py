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

------
See LICENSE.txt for licensing information.
------

"""

from nluas.ntuple_decoder import *
from nluas.core_agent import *
import random
import sys, traceback
import json



#path = os.getcwd() + "/src/main/nluas/"
path = os.path.dirname(os.path.realpath(__file__))

def check_complexity(n):
    s = int(n)
    if s not in [1, 2, 3]:
        raise argparse.ArgumentTypeError("{} is an invalid entry for the complexity level. Should be 1, 2, or 3.".format(n))
    return s

class CoreProblemSolver(CoreAgent):

    def __init__(self, args):
        self.__path__ = os.getcwd() + "/src/main/nluas/"
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
        self.p_features = None
        self.eventFeatures=None
        self.parameter_templates = OrderedDict()
        #self.initialize_templates()
        


    def setup_solver_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-c", "--complexity", default=1, type=check_complexity, help="indicate level of complexity: 1, 2, or 3.")
        return parser

    def callback(self, ntuple):
        self.solve(ntuple)

    def initialize_templates(self):
        """ Initializes templates from path, set above. """
        self.parameter_templates = self.read_templates(self.__path__+"parameter_templates.json")

    def request_clarification(self, ntuple, message="This ntuple requires clarification."):
        new = self.decoder.convert_to_JSON(ntuple)
        request = {'ntuple': new, 'message': message, 'type': 'clarification', 'tag': self.address}
        self.transport.send(self.ui_address, json.dumps(request))

    def identification_failure(self, message):
        request = {'type': 'id_failure', 'message': message, 'tag': self.address}
        self.transport.send(self.ui_address, json.dumps(request))

    def respond_to_query(self, message):
        request = {'type': 'response', 'message': message, 'tag': self.address}
        self.transport.send(self.ui_address, json.dumps(request))

    def return_error_descriptor(self, message):
        request = {'type': 'error_descriptor', 'message': message, 'tag': self.address}
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
                self.p_features = None # Testing, took it out from route_action
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
        #parameters = ntuple['eventDescriptor']
        #self.route_event(parameters, "assertion")

        self.decoder.pprint_ntuple(ntuple)

    def solve_conditional_imperative(self, ntuple):
        self.decoder.pprint_ntuple(ntuple)

    def solve_conditional_declarative(self, ntuple):
        self.decoder.pprint_ntuple(ntuple)

    def route_event(self, eventDescription, predicate):
        features = eventDescription['e_features']
        if features:
            # Set eventFeatures
            self.eventFeatures = features['eventFeatures']
        parameters = eventDescription['eventProcess']
        return_value = self.route_action(parameters, predicate)
        self.eventFeatures = None
        if return_value:
            if predicate == "query":
                #print("Responding via n-tuple...")
                self.respond_to_query(return_value)
            elif predicate == "command":
                self.return_error_descriptor(return_value)
                return return_value


    def route_action(self, parameters, predicate):
        if "complexKind" in parameters and parameters['complexKind'] == "serial":
            return self.solve_serial(parameters, predicate)
        elif "complexKind" in parameters and parameters['complexKind'] == "causal":
            return self.solve_causal(parameters, predicate)
        else:
            template = parameters['template']
            action = parameters['actionary']
            try:
                #if "processFeatures" in parameters['p_features']:
                if parameters['p_features']:
                    self.p_features = parameters['p_features']['processFeatures']
                dispatch = getattr(self, "{}_{}".format(predicate, action))
                return_value = dispatch(parameters)
                self.history.insert(0, (parameters, True))
                self.p_features = None
                return return_value
            except AttributeError as e:
                traceback.print_exc()
                message = "I cannot solve the '{}_{}' action".format(predicate,action)
                self.history.insert(0, (parameters, False))
                self.identification_failure(message)

    def close(self):
        return

    def solve_serial(self, parameters, predicate):
        print(parameters)

    def solve_serial(self, parameters, predicate):
        print(parameters)

    def check_for_clarification(self, ntuple):
        """ Will need to be replaced by a process that checks whether ntuple needs clarification.
        Requires some sort of context/world model. """
        #return random.choice([True, False])
        return False

if __name__ == '__main__':
    ps = CoreProblemSolver(sys.argv[1:])

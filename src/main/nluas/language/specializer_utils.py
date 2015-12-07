"""
.. The SpecalizerTools module performs basic operations to gather information from a SemSpec
    and output an n-tuple.

.. moduleauthor:: Sean Trott <seantrott@icsi.berkeley.edu>

"""


""" ADDED STUFF """
"""*****"""

import sys, traceback
import copy
from copy import deepcopy
import pickle
import time
import json
from pprint import pprint
from nluas.feature import as_featurestruct, StructJSONEncoder
from json import dumps
from nluas.utils import flatten, update, Struct
from itertools import chain
try:
    # Python 2?
    from xmlrpclib import ServerProxy, Fault  # @UnresolvedImport @UnusedImport
except:
    # Therefore it must be Python 3.
    from xmlrpc.client import ServerProxy, Fault #@UnusedImport @UnresolvedImport @Reimport

from os.path import basename
from nluas.language.analyzer_proxy import Analyzer
# from pprint import pprint, pformat


def updated(d, *maps, **entries):
    """A "functional" version of update...
    """
    dd = dict(**d) if isinstance(d, dict) else Struct(d)
    return update(dd, *maps, **entries)

# This just defines the interface
class NullSpecializer(object):
    def specialize(self, fs): 
        """Specialize fs into task-specific structures.
        """
        abstract  # @UndefinedVariable

class DebuggingSpecializer(NullSpecializer):
    def __init__(self):
        self.debug_mode = False

        # Original input sentence
        self._sentence = None

    """ Sets debug_mode to ON/OFF """
    def set_debug(self):
        self.debug_mode = not self.debug_mode 


class ReferentResolutionException(Exception):
    def __init__(self, message):
        self.message = message


class FeatureStructException(Exception):
    def __init__(self, message):
        self.message = message

class MoodException(FeatureStructException):
    def __init__(self, message):
        self.message = message


class UtilitySpecializer(DebuggingSpecializer):
    def __init__(self, analyzer):
        self._stacked = []
        DebuggingSpecializer.__init__(self)
        self.analyzer = analyzer
        #self.mapping_reader = MappingReader()
        #self.mapping_reader.read_file(self.analyzer.get_mapping_path())
        self.mappings = self.analyzer.get_mappings()
        self.event = True


    def is_compatible(self, typesystem, role1, role2):
        return self.analyzer.issubtype(typesystem, role1, role2) or self.analyzer.issubtype(typesystem, role2, role1)

    """ Input PROCESS, searches SemSpec for Adverb Modifiers. Currently just returns speed,
    but could easily be modified to return general manner information. This might be made more complex
    if we wanted to describe more complex motor routines with adverbs. """
    def get_actionDescriptor(self, process):
        tempSpeed = .5
        returned=dict(speed=tempSpeed)
        if hasattr(process, "speed") and str(process.speed) != "None":
            tempSpeed = float(process.speed)
            returned['speed'] = float(process.speed)
        for i in process.__features__.values():
            for role, filler in i.__items__():
                if filler.typesystem() == 'SCHEMA' and self.analyzer.issubtype('SCHEMA', filler.type(), 'AdverbModification'):
                    if process.index() == filler.modifiedThing.index():
                        if (filler.value) and (filler.property.type() == "speed"):
                            newSpeed = float(filler.value)
                            if min(newSpeed, tempSpeed) < .5:
                                #return min(newSpeed, tempSpeed)
                                returned['speed'] = min(newSpeed, tempSpeed)
                            else:
                                returned['speed'] = max(newSpeed, tempSpeed)
                                #return max(newSpeed, tempSpeed)
                            #return float(filler.value)
                        elif (filler.value) and (filler.property.type() == "process_kind"):
                            returned['collaborative'] = filler.value.type()
                            #return filler.value.type()
                        else:
                            returned['collaborative'] = False
                            #return False
        return returned

    """ This returns a string of the specified relation of the landmark to the other RD, based on the values
    and mappings encoded in the SemSpec. This needs to be fixed substantially.
    """
    def get_locationDescriptor(self, goal):
        #location = {}
        location = ''
        for i in goal.__features__.values():
            for role, filler in i.__items__():
                if filler.type() == 'Sidedness':
                    if filler.back.index() == goal.index():
                        return 'behind' #location = 'behind'
                elif filler.type() == 'BoundedObject':
                    if filler.interior.index() == goal.index():
                        if i.m.type() == "TrajectorLandmark":
                            return "in"
                        elif i.m.type() == "SPG":
                            return 'into'
                elif filler.type() == "NEAR_Locative":
                    if filler.p.proximalArea.index() == goal.index(): #i.m.profiledArea.index(): 
                        location = 'near'    
                        #location['relation'] = 'near' 
                elif filler.type() == "AT_Locative":
                    if filler.p.proximalArea.index() == goal.index():
                        location = 'at' 
                        #location['relation'] = 'at'    
        return location 


    def invert_pointers(self, goal):
        final = {}
        for i in goal.__features__.values():
            for roles, filler in i.__items__():
                # Checks: filler is schema, it exists, and it has a temporalitly
                if filler.typesystem() == "SCHEMA" and filler:
                    for k, v in filler.__items__():
                        if v.index() == goal.index():
                            if filler.type() not in final:
                                final[filler.type()] = []
                            final[filler.type()].append(filler)
        return final






    """Depth-first search of sentence to collect values matching object (GOAL). 
    Now just iterates through feature struct values (due to change in FS structure). Returns a dictionary
    of object type, properties, and trajector landmarks.
    """
    def get_objectDescriptor(self, goal, resolving=False):
        if 'referent' in goal.__dir__() and goal.referent.type():
            if goal.referent.type() == "antecedent":
                print(self.resolve_referents())
                return self.resolve_referents()['objectDescriptor']
            elif goal.referent.type() == "anaphora" and not resolving:
                return self.resolve_anaphoricOne(goal)['objectDescriptor']
            #else:
            #    returned = {'referent': goal.referent.type(), 'type': goal.ontological_category.type()}
        elif goal.ontological_category.type() == 'location':
            returned = {'location': (float(goal.xCoord), float(goal.yCoord))}
        returned = {'type': goal.ontological_category.type()}
        if "referent" in goal.__dir__():
            returned['referent'] = goal.referent.type()
        if 'givenness' in goal.__dir__():
            returned['givenness'] = goal.givenness.type()
        if "gender" in goal.__dir__():
            returned['gender'] = goal.gender.type()
        if "number" in goal.__dir__():
            returned['number'] = goal.number.type()
        if "specificWh" in goal.__dir__():
            returned['specificWh'] = goal.specificWh.type()
        for i in goal.__features__.values():
            for roles, filler in i.__items__():
                if filler.typesystem() == 'SCHEMA':
                    if self.analyzer.issubtype('SCHEMA', filler.type(), 'PropertyModifier') and (hasattr(filler, "temporality") and filler.temporality.type() == "atemporal"):
                        if filler.modifiedThing.index() == goal.index():
                            returned['negated'] = False
                            if "negated" in filler.__dir__() and filler.negated.type() == "yes":
                                returned['negated'] = True
                            v = filler.value.type()   
                            if v == "scalarValue":
                                returned[str(filler.property.type())] = float(filler.value)
                            #if v in self.mappings:
                            #    v = self.mappings[v]
                            else:
                                returned[str(filler.property.type())] = v
                            returned['kind'] = str(filler.kind.type())
                            if filler.type() == "ComparativeAdjModifier":
                                returned['base'] == self.get_objectDescriptor(filler.base)
                    elif filler.type() == "TrajectorLandmark" and (hasattr(filler, "temporality") and filler.temporality.type() == "atemporal"):
                        if filler.trajector.index() == goal.index():
                            l = self.get_objectDescriptor(filler.landmark)
                            relation = self.get_locationDescriptor(filler.profiledArea)
                            locationDescriptor = {'objectDescriptor': l, 'relation': relation}
                            returned['locationDescriptor'] = locationDescriptor  

                    #if filler.type() == "EventDescriptor" and (filler.modifiedThing and filler.modifiedThing.index() == goal.index()):
                    #    print(filler.eventProcess.type()  
                    if filler.type() == "EventDescriptor" and hasattr(filler, "modifiedThing"):
                        if (filler.modifiedThing.index() == goal.index()) and self.event:
                            self.event = False
                            returned['processDescriptor'] = self.get_processDescriptor(filler.eventProcess, goal)  
                            self.event = True                       
        return returned   

    def get_processDescriptor(self, process, referent):
        """ Retrieves information about a process, according to existing templates. Meant to be implemented 
        in specific extensions of this interface. 

        Can be overwritten as needed -- here, it calls the params_for_compound to gather essentially an embedded n-tuple.
        """
        return list(self.params_for_compound(process))

    """ Meant to match 'one-anaphora' with the antecedent. As in, "move to the big red box, then move to another one". Or,
    'He likes the painting by Picasso, and I like the one by Dali.' Not yet entirely clear what information to encode 
    besides object type. """
    def resolve_anaphoricOne(self, item):
        popper = list(self._stacked)
        while len(popper) > 0:
            ref = popper.pop()
            while ('location' in ref or 'locationDescriptor' in ref or 'referent' in ref['objectDescriptor']) and len(popper) > 0:
                ref = popper.pop()
            if item.givenness.type() == 'distinct':
                return {'objectDescriptor': {'type': ref['objectDescriptor']['type'], 'givenness': 'distinct'}} 
            else:
                test = self.get_objectDescriptor(item, resolving=True)
                merged = self.merge_descriptors(ref['objectDescriptor'], test)
                return {'objectDescriptor': merged}
        raise ReferentResolutionException("Sorry, I don't know what you mean by 'one'.")


    def merge_descriptors(self, old, new):
        """ Merges object descriptors from OLD and NEW. Objective: move descriptions / properties from OLD
        into NEW unless NEW conflicts. If a property conflicts, then use the property in NEW. """
        if 'referent' in new and new['referent'] in ['anaphora', 'antecedent']:
            new.pop("referent")
        for key, value in old.items():
            if key == 'type':
                new[key] = old[key]
            if not key in new:
                new[key] = old[key]
        return new
        
    """ Simple reference resolution gadget, meant to unify object pronouns with potential
    antecedents. """
    def resolve_referents(self, actionary=None, pred=None):
        popper = list(self._stacked)
        while len(popper) > 0:
            ref = popper.pop()
            if self.resolves(ref, actionary, pred):
                if 'partDescriptor' in ref:
                    return ref['partDescriptor']
                return ref
        raise ReferentResolutionException("Sorry, I did not find a suitable referent found in past descriptions.")

    """ Returns a boolean on whether or not the "popped" value works in the context provided. """
    def resolves(self, popped, actionary=None, pred=None):
        if actionary == 'be2' or actionary == 'be':
            if 'location' in popped or 'locationDescriptor' in popped:
                return 'relation' in pred
            else:
                if 'referent' in popped:
                    test = popped['referent'].replace('_', '-')
                    return self.analyzer.issubtype('ONTOLOGY', test, 'physicalEntity')
                else:
                    return self.analyzer.issubtype('ONTOLOGY', popped['objectDescriptor']['type'], 'physicalEntity')
        if actionary == 'forceapplication' or actionary == 'move':
            if 'location' in popped or 'locationDescriptor' in popped:
                return False
            if 'partDescriptor' in popped:
                pd = popped['partDescriptor']['objectDescriptor']
                if 'referent' in pd:
                    return self.analyzer.issubtype('ONTOLOGY', pd['referent'].replace('_', '-'), 'moveable')
                else:
                    return self.analyzer.issubtype('ONTOLOGY', pd['type'], 'moveable')
            else:
                if 'objectDescriptor' in popped and 'type' in popped['objectDescriptor']:
                    return self.analyzer.issubtype('ONTOLOGY', popped['objectDescriptor']['type'], 'moveable')
                return False
        # If no actionary passed in, no need to check for context
        return True      

    def replace_mappings(self, ntuple):
        """ This is supposed to replace all of the mappings in the ntuple with values from the action ontology, if applicable. """
        n = ntuple
        if type(ntuple) == Struct:
            n = ntuple.__dict__
        for k,v in n.items():
            if type(v) == dict or type(v) == Struct:
                n[k]= self.replace_mappings(v)
            elif type(v) == list:
                for value in v:
                    value = self.replace_mappings(value)
            elif v is None:
                continue
            elif v in self.mappings:
                n[k] = self.mappings[v]
                v = self.mappings[v]
        return n

    def map_ontologies(self, ntuple):
        """ This is supposed to replace all of the mappings in the ntuple with values from the action ontology, if applicable. """
        n = ntuple
        for k, v in ntuple.items():
            if isinstance(v, dict):
                n[k] = self.map_ontologies(v)
            elif isinstance(v, list):
                for value in v:
                    value = self.map_ontologies(value)
            elif v is None:
                continue
            elif v in self.mappings:
                n[k] = self.mappings[v]
                v = self.mappings[v]
        return n



class TemplateSpecializer(NullSpecializer):
    def __init__(self):

        self._wrapper = dict(predicate_type=None,             
                              parameters=None, # one of (_execute, _query)                         
                              return_type='error_descriptor') 

        self._general = dict(kind="unknown",
                             action=None,
                             protagonist=None,
                             p_features=None)

        # Assertion: "the box is red"
        self._assertion = dict(kind='assertion',  # might need to change parameters
                             action=None,
                             protagonist=None,
                             predication=None,
                             p_features=None)    


        self._WH = dict(kind = 'query',
                        protagonist = None,
                        action = None,
                        predication = None,
                        specificWh = None,
                        p_features=None)


        #Y/N dictionary: is the box red?
        self._YN = dict(kind = 'query',
                        protagonist=None,
                        action=None,
                        predication=None,
                        p_features=None)

        # Basic executable dictionary
        self._execute = dict(kind='execute',
                             control_state='ongoing', 
                             action=None,
                             protagonist=None,
                             #distance=Struct(value=4, units='square'),
                             #goal=None,
                             #speed = .5,
                             #heading=None, #'north',
                             #direction=None,
                             collaborative=False,
                             p_features=None)


        # Conditional Imperative
        self._conditional_imperative = dict(kind='conditional_imperative',
                                 condition=self._YN,  # Maybe should be template for Y/N question?
                                 command = self._execute)

        # Conditional Imperative
        self._conditional_declarative = dict(kind='conditional_declarative',
                                 condition=None,  # Maybe should be template for Y/N question?
                                 assertion = self._assertion)

        # TESTING: Causal dictionary: "Robot1, move the box to location 1 1!"
        self._cause = dict(kind = 'cause',
                           causer = None,
                           action = None,
                           collaborative=False,
                           p_features=None)



class RobotTemplateSpecializer(TemplateSpecializer):
    def __init__(self):

        TemplateSpecializer.__init__(self)

        """
        # Basic executable dictionary
        self._execute = dict(kind='execute',
                             control_state='ongoing', 
                             action=None,
                             protagonist=None,
                             distance={"value": .5, "units":'square'},
                             goal=None,
                             speed = .5,
                             heading=None, #'north',
                             direction=None,
                             collaborative=False)
        """






 






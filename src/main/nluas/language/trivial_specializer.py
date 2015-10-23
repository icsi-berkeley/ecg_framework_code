"""
Author: seantrott <seantrott@icsi.berkeley.edu>

Developing/Testing a new method for specializers. 
"""

from nluas.language.specializer_utils import *
from nluas.utils import *
import pickle


class TrivialSpecializer(TemplateSpecializer, UtilitySpecializer):

    def __init__(self, analyzer_port):

        UtilitySpecializer.__init__(self, analyzer_port)
        TemplateSpecializer.__init__(self)

        self.predicates = {'Declarative': 'assertion',
                           'WH_Question': 'query',
                           'YN_Question': 'query',
                           'Imperative': 'command'}

    def specialize(self, fs):
        predicate_type = str(fs.m.mood)
        ntuple = {'predicate_type': self.predicates[predicate_type]}
        ntuple['params'] = self.process_params(fs.m.content.eventProcess)
        return ntuple


    def process_params(self, process):
        ntuple = {}
        indices = []
        if process != None:
            for role, filler in process.__items__():
                if filler and filler.index() not in indices:
                    indices.append(filler.index())
                    if filler.typesystem() == "SCHEMA":
                        print("{}_params".format(filler.type().lower()))
                        if self.analyzer.issubtype('SCHEMA', filler.type(), "RD"):
                            ntuple[str(role)] = {'objectDescriptor': self.get_objectDescriptor(filler)}
                        elif hasattr(self, "{}_params".format(filler.type().lower())):
                            dispatch = getattr(self, "{}_params".format(filler.type().lower()))
                            ntuple[filler.type().lower()] = dispatch(filler)
                    elif filler.typesystem() == "ONTOLOGY":
                        ntuple[str(role)] = filler.type()
        return ntuple

    def propertymodifier_params(self, pm):
        ntuple = {}
        ntuple['predication'] = {pm.property.type(): pm.value.type()}
        return ntuple







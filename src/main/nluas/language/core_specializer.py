"""
module author: Sean Trott <seantrott@icsi.berkeley.edu>

The Core Specializer performs some basic operations in converting a SemSpec to an n-tuple.

Crucial to its design is the notion of templates, which contain specifications for filling in the n-tuple.
Templates should be defined declaratively.

"""

from nluas.language.specializer_utils import *
from nluas.language.analyzer_proxy import *
from nluas.utils import *
from collections import OrderedDict
import pickle
import json
import os
import itertools
import time
path = os.getcwd() + "/src/main/nluas/"


class CoreSpecializer(TemplateSpecializer, UtilitySpecializer):

    def __init__(self, analyzer):

        UtilitySpecializer.__init__(self, analyzer)
        TemplateSpecializer.__init__(self)
        self.parameter_templates = OrderedDict() #self.read_templates(path+"parameter_templates.json")
        self.mood_templates = OrderedDict() #self.read_templates(path+"mood_templates.json")
        self.descriptor_templates = OrderedDict()
        #self.wrapper_templates = self.read_templates(path+"templates.json")
        self.initialize_templates()


        #testing
        self.protagonist = None

        #self.read_templates

    def initialize_templates(self):
        self.parameter_templates = self.read_templates(path+"parameter_templates.json")
        self.mood_templates = self.read_templates(path+"mood_templates.json")
        self.descriptor_templates = self.read_templates(path+"descriptors.json")
        self.event_templates = self.read_templates(path + "event_templates.json")

    def read_templates(self, filename):
        #print("Parsing " + filename)
        base = OrderedDict()
        with open(filename, "r") as data_file:
            #data = json.loads(data_file.read())
            data = json.load(data_file, object_pairs_hook=OrderedDict)
            for name, template in data['templates'].items():
                setattr(self, name, template)
                base[name] = template
                #self.__dict__[name] = template
        return base

    def specialize_event(self, content):
        ed = content.type()
        if ed in self.event_templates:
            template = self.event_templates[ed]
        else:
            template = self.event_templates[self.check_parameter_subtypes(ed, self.event_templates)]
        eventDescriptor = dict()
        for k, v in template.items():
            eventDescriptor[k] = self.fill_value(k, v, content)
        return eventDescriptor


    def specialize(self, fs):
        mood = str(fs.m.mood).replace("-", "_").lower()
        content = fs.m.content
        eventProcess = fs.m.content.eventProcess
        ntuple = self.mood_templates[mood]
        ntuple['eventDescriptor'] = self.specialize_event(content)
        #if content.type() in self.event_templates:
        #    ntuple['parameters'] = [self.specialize_event(content)]
            #return ntuple
        #else:
        #parameters = self.fill_parameters(eventProcess)
        #ntuple['parameters'] = [parameters]
        parameters = ntuple['eventDescriptor']['eventProcess']
        if mood == "wh_question":
            ntuple['return_type'], ntuple['eventDescriptor']['eventProcess']['specificWh'] = self.get_return_type(parameters)

        ntuple = self.map_ontologies(ntuple)

        if self.debug_mode:
            print(ntuple)
        return dict(ntuple)


    def get_return_type(self, parameters):
        return_type, specificWh = "", ""
        returns = {'plural': "collection_of",
                 "singular": "singleton",
                 "which": "instance_reference",
                 "where": "instance_reference",
                 "what": "class_reference"}
        for k, v in parameters.items():
            if isinstance(v, dict):
                if ("objectDescriptor" in v and "specificWh" in v['objectDescriptor']):
                    number, specificWh = v['objectDescriptor']['number'], v['objectDescriptor']['specificWh']
                    return_type += returns[number] + "::" + returns[specificWh]
                    return return_type, specificWh
                elif  "eventRDDescriptor" in v and "specificWh" in v['eventRDDescriptor']:
                    number, specificWh = v['eventRDDescriptor']['number'], v['eventRDDescriptor']['specificWh']
                    return_type += returns[number] + "::" + returns[specificWh]
                    return return_type, specificWh
                else:
                    r, w = self.get_return_type(v)
                    if r != "" and w != "":
                        return r, w

        return return_type, specificWh


    def fill_parameters(self, eventProcess):
        process = eventProcess.type()
        if process in self.parameter_templates:
            template = self.parameter_templates[process]
        elif self.check_parameter_subtypes(process, self.parameter_templates):
            subtype = self.check_parameter_subtypes(process, self.parameter_templates)
            template = self.parameter_templates[subtype]
        else:
            template = self.parameter_templates["Process"]
        parameters = dict()
        for key, value in template.items():
            parameters[key] = self.fill_value(key, value, eventProcess)
        return parameters


    def check_parameter_subtypes(self, process, templates):
        for key in templates:
            if self.analyzer.issubtype("SCHEMA", process, key):
                return key
        return None

    def fill_value(self, key, value, eventProcess):
        final_value = None
        if isinstance(value, dict):
            if "method" in value and hasattr(eventProcess, key):
                method = getattr(self, value["method"])
                return method(eventProcess)
            elif "descriptor" in value:
                method = getattr(self, "get_{}".format(value["descriptor"]))
                if hasattr(eventProcess, key) and getattr(eventProcess, key).__bool__():
                    attribute = getattr(eventProcess, key)
                    descriptor = {value['descriptor']: method(attribute)}
                    # HACK: 
                    if value['descriptor'] == "objectDescriptor":# and not self.analyzer.issubtype("ONTOLOGY", descriptor['objectDescriptor']['type'], "sentient"):
                        self._stacked.append(descriptor)
                    if key == "protagonist":
                        self.protagonist = descriptor
                    return descriptor
                if "default" in value:
                    return value['default']
                return None
            elif "parameters" in value and hasattr(eventProcess, value['parameters']):
                return self.fill_parameters(getattr(eventProcess, value['parameters']))
            elif "eventDescription" in value and hasattr(eventProcess, value['eventDescription']):
                return self.specialize_event(getattr(eventProcess, value['eventDescription']))
        elif value and hasattr(eventProcess, key):
            attribute = getattr(eventProcess, key)
            if attribute.type() == "scalarValue":
                return float(attribute)
            return attribute.type()
        return final_value

    def get_scaleDescriptor(self, scale):
        return {'units': scale.units.type(), 'value': float(scale.amount.value)}

    def get_property(self, pm):
        returned = {}
        negated = False
        kind = pm.kind.type()
        if hasattr(pm, "negated") and pm.negated.type() == "yes":
            negated = True
        if hasattr(pm, "value"):
            value = pm.value.type()
            if value == "scalarValue":
                value = float(pm.value)
            returned[pm.property.type()] = value
            returned['property'] = pm.property.type()
        if hasattr(pm, "direction"):
            returned['direction'] = pm.direction.type()
        elif self.analyzer.issubtype("ONTOLOGY", pm.property.type(), "scale") and kind == "comparative":
            if value > .5:
                returned['direction'] = "increase"
            else:
                returned['direction'] = 'decrease'
        returned['negated'] = negated
        return returned


    def get_state(self, eventProcess):
        predication = {}
        state = eventProcess.state
        predication['negated'] = False
        if self.analyzer.issubtype("SCHEMA", state.type(), "PropertyModifier"):
            predication = self.get_property(state)
            if self.protagonist and "property" in self.protagonist['objectDescriptor']:
                prop1, prop2  = predication['property'], self.protagonist['objectDescriptor']['property']['objectDescriptor']['type']
                if not self.is_compatible('ONTOLOGY', prop1, prop2):
                    raise Exception("Problem with analysis: the predication '{}' is not compatible with '{}'".format(prop1, prop2))
        elif self.analyzer.issubtype("SCHEMA", state.type(), "QuantifiedRD"):
            predication['amount'] = self.get_scaleDescriptor(state)
        elif self.analyzer.issubtype("SCHEMA", state.type(), "TrajectorLandmark"):
            predication['relation']= self.get_locationDescriptor(state.profiledArea) 
            predication['objectDescriptor'] = self.get_objectDescriptor(state.landmark)
        elif self.analyzer.issubtype('SCHEMA', state.type(), 'RefIdentity'):
            predication['identical']= {'objectDescriptor': self.get_objectDescriptor(state.second)}
        return predication

    def get_spgDescriptor(self, spg):
        descriptor = self.descriptor_templates['spgDescriptor']
        final = {'goal': None,
                 'source': None,
                 'path': None}
        if hasattr(spg, "goal") and spg.goal:
            final['goal'] = self.get_spgValue(spg, "goal")
        if hasattr(spg, "source") and spg.source:
            final['source'] = self.get_spgValue(spg, "source")
        if hasattr(spg, "path") and spg.path:
            final['path'] = self.get_spgValue(spg, "path")
        return final

    def get_spgValue(self, spg, valueType):
        final = {}
        value = getattr(spg, valueType)
        
        if value.ontological_category.type() == "location":
            return {'location': (float(value.xCoord), float(value.xCoord))}
        if value.index() == spg.landmark.index():
            return {'objectDescriptor': self.get_objectDescriptor(value)}
        if value.type() == "RD":
            return {'objectDescriptor': self.get_objectDescriptor(value)}

        return final


    def get_processFeatures(self, p_features):
        features = self.descriptor_templates['processFeatures']
        final = {}
        for k, v in features.items():
            if k in p_features.__dir__():
                final[k] = getattr(p_features, v).type()
        return final

    def get_eventFeatures(self, e_features):
        features = self.descriptor_templates['eventFeatures']
        final = {}
        for k, v in features.items():
            if k in e_features.__dir__():
                value = getattr(e_features, v).type()
                if k == "negated":
                    if value == "yes":
                        final[k] = True
                    else:
                        final[k] = False
                else:
                    final[k] = value
        return final

    def get_objectDescriptor(self, item, resolving=False):
        if 'referent' in item.__dir__() and item.referent.type():
            if item.referent.type() == "antecedent":
                return self.resolve_referents()['objectDescriptor']
            elif item.referent.type() == "anaphora" and not resolving:
                return self.resolve_anaphoricOne(item)['objectDescriptor']
        if "pointers" not in item.__dir__():
            item.pointers = self.invert_pointers(item)
        template = self.descriptor_templates['objectDescriptor']
        returned = {}
        for k, v in template.items():
            if k not in ["pointers", "description"] and hasattr(item, v):# and getattr(item, v).type():
                attribute = getattr(item, v).type()
                if attribute:
                    returned[k] = attribute
        for pointer, mod in item.pointers.items():
            # TODO: check if it's a subcase as well? or don't do this
            if pointer in template['pointers']:
                filler = self.fill_pointer(mod, item)
                if filler:
                    returned.update(filler)
        return returned

    def get_eventRDDescriptor(self, item):
        # TODO: Event/entity resolution?
        returned = self.get_objectDescriptor(item)
        eventDescription = dict()
        if hasattr(item, "description") and item.description:
            eventForm = item.description.eventForm.type()
            eventDescription['eventForm'] = eventForm
            if eventForm != "lexical":
                eventDescription['eventDescription'] = self.specialize_event(item.description)
            else:
                eventDescription['description'] = None
        returned.update(eventDescription)
        return returned


    def fill_pointer(self, pointer, item):
        if hasattr(pointer, "modifiedThing") and pointer.modifiedThing.index() != item.index():
            return None
        elif hasattr(pointer, "temporality") and pointer.temporality.type() != "atemporal":
            return None
        elif hasattr(pointer, "trajector") and pointer.trajector.index() != item.index():
            return None
        else:
            if self.analyzer.issubtype('SCHEMA', pointer.type(), "PropertyModifier"):
                if pointer.value.type() == "scalarValue":
                    return {pointer.property.type(): float(pointer.value)}
                return {pointer.property.type(): pointer.value.type()}
            elif self.analyzer.issubtype("SCHEMA", pointer.type(), "TrajectorLandmark"):
                relation = self.get_locationDescriptor(pointer.profiledArea)
                landmark = self.get_objectDescriptor(pointer.landmark)
                return {'locationDescriptor': {'relation': relation,
                                               'objectDescriptor': landmark}}
            elif self.analyzer.issubtype("SCHEMA", pointer.type(), "EventDescriptor") and self.event and hasattr(pointer, "modifiedThing"):
                self.event = False
                process= {'processDescriptor': self.get_processDescriptor(pointer.eventProcess, item)}
                self.event = True
                return process
            elif self.analyzer.issubtype("SCHEMA", pointer.type(), "Modification"):# and pointer.modifier.type() == "RD":
                return dict(property=dict(objectDescriptor=self.get_objectDescriptor(pointer.modifier)))


    def get_processDescriptor(self, process, referent):
        """ Retrieves information about a process, according to existing templates. Meant to be implemented 
        in specific extensions of this interface. 

        Can be overwritten as needed -- here, it calls the params_for_compound to gather essentially an embedded n-tuple.
        """
        return self.fill_parameters(process)



#analyzer = Analyzer("http://localhost:8090")
#cs = CoreSpecializer(analyzer)


#parse = analyzer.parse("if the box that John sees is big, it is not red.")[0]

#s = cs.specialize(parse)

#parse = analyzer.parse("the box that he saw")[0]
#parse = analyzer.parse("Robot1, move north then move south then move west!")[0]
#parse = analyzer.parse("Robot1, move north then move south!")[0]
#parse = analyzer.parse("he moved to the box.")[0]







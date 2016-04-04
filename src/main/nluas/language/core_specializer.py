"""
module author: Sean Trott <seantrott@icsi.berkeley.edu>

The Core Specializer performs some basic operations in converting a SemSpec to an n-tuple.

Crucial to its design is the notion of templates, which contain specifications for filling in the n-tuple.
Templates should be defined declaratively; the definitions in the template provide instructions
to the Specializer for how to fill in each value.

See notes on individual methods for more details, as well as documentation here:
* https://embodiedconstructiongrammar.wordpress.com/2016/02/12/core-specializer-draft


The crucial interface methods include:
* specialize(self, fs)
* specialize_event(self, fs)
* fill_parameters(self, eventProcess)
* fill_value(self, eventProcess)

As a general rule for template-building:
* If a slot in a grammar schema has a "filler", e.g. another schema (like "RD"),
  the template filler for that role should have a "descriptor" (objectDescriptor).
* If a slot in the grammar schema just maps onto an ontology item or string value,
  the value in the template should be the role name.
* QUESTION: if no value is found, should fill_value return the "value" in the template, or None? (probably the former?)

NOTES / TODO:
* Referent resolution for embedded phrases ("is box1 near the box" "which box" "the blue one" --> should resolve with blue box, not box1)
* Better specialization of sentence fragments

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


class CoreSpecializer(UtilitySpecializer):

    def __init__(self, analyzer):

        self.fs = None
        UtilitySpecializer.__init__(self, analyzer)
        self.parameter_templates = OrderedDict() #self.read_templates(path+"parameter_templates.json")
        self.mood_templates = OrderedDict() #self.read_templates(path+"mood_templates.json")
        self.descriptor_templates = OrderedDict()
        self.initialize_templates()

        self.protagonist = None

        self.negated = {'yes': True,
                        'no': False,
                        'boolean': False}

        self.spans = None

        #self.read_templates

    def set_spans(self, spans):
        """ Sets the current constructional spans to input spans. These are used for referent resolution. (TODO)."""
        self.spans = spans

    def specialize_fragment(self, fs):
        """ Specializes a sentence fragment, e.g. 'the red one' or a non-discourse-utterance. """
        if not hasattr(fs, "m") or fs.m == "None":
            return None
        elif self.analyzer.issubtype("SCHEMA", fs.m.type(), "RD"):
            return self.get_objectDescriptor(fs.m)
        elif self.analyzer.issubtype("SCHEMA", fs.m.type(), "PropertyModifier"):
            return self.get_property(fs.m)
        elif self.analyzer.issubtype("SCHEMA", fs.m.type(), "EventDescriptor"):
            return self.specialize_event(fs.m)
        elif self.analyzer.issubtype("SCHEMA", fs.m.type(), "Process"):
            return self.fill_parameters(fs.m)
        elif self.analyzer.issubtype("SCHEMA", fs.m.type(), "SPG"):
            return self.get_spgDescriptor(fs.m)
        elif self.analyzer.issubtype("SCHEMA", fs.m.type(), "Relation"):
            s = self.get_relationDescriptor(fs.m)
            return self.get_relationDescriptor(fs.m)
        elif self.analyzer.issubtype("SCHEMA", fs.m.type(), "TrajectorLandmark"):
            return {"locationDescriptor": {"relation": self.get_locationDescriptor(fs.m.profiledArea),
                                            "objectDescriptor": self.get_objectDescriptor(fs.m.landmark)}}
        else:
            print("Unable to specialize fragment with meaning of {}.".format(fs.m.type()))

    def initialize_templates(self):
        """ Initializes templates from path, set above. """
        self.parameter_templates = self.read_templates(path+"parameter_templates.json")
        self.mood_templates = self.read_templates(path+"mood_templates.json")
        self.descriptor_templates = self.read_templates(path+"descriptors.json")
        self.event_templates = self.read_templates(path + "event_templates.json")

    def read_templates(self, filename):
        """ Sets each template to ordered dict."""
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
        """ Takes in an EventDescriptor, and uses event_templates to drive specialization. 
        Calls fill_value for each item in the corresponding event template. """
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
        """ Takes in a FeatureStruct (fs), produces an ntuple. 
        Currently requires that the FS be a discourse utterance with a mood ("Declarative", etc.),
        and an associated EventDescriptor. However, this could be generalized to route
        specialized n-tuples for other types of input, like an NP.
        """
        if fs.m.type() != "DiscourseElement":
            ntuple = self.specialize_fragment(fs)
        else:
            self.fs = fs
            mood = str(fs.m.mood).replace("-", "_").lower()
            content = fs.m.content
            eventProcess = fs.m.content.eventProcess
            ntuple = self.mood_templates[mood]
            ntuple['eventDescriptor'] = self.specialize_event(content)
            if 'eventProcess' in ntuple['eventDescriptor']:
                parameters = ntuple['eventDescriptor']['eventProcess']
                if mood == "wh_question":
                    ntuple['return_type'], ntuple['eventDescriptor']['eventProcess']['specificWh'] = self.get_return_type(parameters)
        
        if ntuple:
            ntuple = self.map_ontologies(ntuple)

            if self.debug_mode:
                print(ntuple)
            return dict(ntuple)


    def get_return_type(self, parameters):
        """ If sentence is a wh-sentence, returns the corresponding return_type. """
        return_type, specificWh = "", ""
        returns = {'plural': "collection_of",
                 "singular": "singleton",
                 "which": "instance_reference",
                 "where": "instance_reference",
                 "what": "class_reference"}
        for k, v in parameters.items():
            if isinstance(v, dict):
                if ("objectDescriptor" in v and "specificWh" in v['objectDescriptor']) and v['objectDescriptor']['specificWh']:
                    number, specificWh = v['objectDescriptor']['number'], v['objectDescriptor']['specificWh']
                    return_type += returns[number] + "::" + returns[specificWh]
                    return return_type, specificWh
                elif  "eventRDDescriptor" in v and "specificWh" in v['eventRDDescriptor'] and v['eventRDDescriptor']['specificWh']:
                    number, specificWh = v['eventRDDescriptor']['number'], v['eventRDDescriptor']['specificWh']
                    return_type += returns[number] + "::" + returns[specificWh]
                    return return_type, specificWh
                else:
                    r, w = self.get_return_type(v)
                    if r != "" and w != "":
                        return r, w
        return return_type, specificWh


    def fill_parameters(self, eventProcess):
        """ Identifies the corresponding parameter template ("MotionPath", etc.). 
        If none are found, it chooses a parent template ("Motion", "Process", etc.).
        For each item in the template, it calls fill_value. """
        process = eventProcess.type()
        template_name = process
        if process in self.parameter_templates:
            template = self.parameter_templates[process]
        elif self.check_parameter_subtypes(process, self.parameter_templates):
            subtype = self.check_parameter_subtypes(process, self.parameter_templates)
            template_name = subtype
            template = self.parameter_templates[subtype]
        else:
            template = self.parameter_templates["Process"]
            template_name = "Process"
        parameters = dict()
        for key, value in template.items():
            parameters[key] = self.fill_value(key, value, eventProcess)

        if self.analyzer.issubtype("SCHEMA", process, "Process"):
            pointers = self.get_process_modifiers(eventProcess)
            parameters.update(pointers)
            parameters['schema'] = process    # Maybe make this part of template?
            parameters['template'] = template_name
        return parameters

    def get_process_modifiers(self, eventProcess):
        returned = dict()
        eventProcess.pointers = self.invert_pointers(eventProcess)
        template = self.descriptor_templates['Process'] if "Process" in self.descriptor_templates else dict()
        allowed_pointers = template['pointers'] if 'pointers' in template else []
        for pointer, mods in eventProcess.pointers.items():
            if pointer in allowed_pointers:
                for mod in mods:
                    if pointer == "ScalarAdverbModifier":
                        prop, value = mod.property.type(), float(mod.value)
                        returned[prop] = value
                    elif pointer == "AdjunctModification":
                        modifier = mod.modifier
                        print(modifier.type())
                        if modifier.type() == "Accompaniment":
                            returned["co-participant"] = self.get_objectDescriptor(modifier.co_participant)
                        elif modifier.type() == "Instrument":
                            returned["instrument"] = self.get_objectDescriptor(modifier.instrument)
        return returned



    def check_parameter_subtypes(self, process, templates):
        """ Finds the parent type of the input process among the template list. """
        for key in templates:
            if self.analyzer.issubtype("SCHEMA", process, key):
                return key
        return None


    def get_headingDescriptor(self, headingSchema):
        """ Returns a heading for a headingDescriptor. Could be more complex depending on domain,
        in which case the method would be overridden. """
        return headingSchema.tag.type()

    def fill_value(self, key, value, input_schema):
        """ Most important specializer method. Takes in a skeleton key,value pairing from a template,
        as well as the relevant schema ("MotionPath", etc.), and returns the relevant value.
        If the value is a dictionary, it might be a "descriptor", so it returns an objectDescriptor, etc.
        A dictionary value could also indicate an embedded process, in which case fill_parameters is called.
        Also calls specialize_event for embedded EventDescriptors.
        Otherwise, it gets the filler for the value from the schema ("actionary": @move), and returns this.
        """
        final_value = None
        if isinstance(value, dict):
            if "method" in value and hasattr(input_schema, key):
                method = getattr(self, value["method"])
                return method(input_schema)
            elif "descriptor" in value:
                method = getattr(self, "get_{}".format(value["descriptor"]))
                if hasattr(input_schema, key) and getattr(input_schema, key).has_filler():
                    attribute = getattr(input_schema, key)
                    descriptor = {value['descriptor']: method(attribute)}
                    if value['descriptor'] == "objectDescriptor":
                        self._stacked.append(descriptor)
                    if key == "protagonist":
                        self.protagonist = dict(descriptor)
                    return descriptor
                if "default" in value:
                    return value['default']
                return None
            elif "parameters" in value and hasattr(input_schema, value['parameters']):
                return self.fill_parameters(getattr(input_schema, value['parameters']))
            elif "eventDescription" in value and hasattr(input_schema, value['eventDescription']) and getattr(input_schema, value['eventDescription']).has_filler():
                return self.specialize_event(getattr(input_schema, value['eventDescription']))
        elif value and hasattr(input_schema, key):
            attribute = getattr(input_schema, key)
            if attribute.type() == "scalarValue":
                return float(attribute)
            elif key == "negated":
                return self.get_negated(attribute.type())
            elif attribute.type() != "None" and attribute.type() != None:
                return attribute.type()
            elif attribute.__value__ != "None":
                return attribute.__value__
            print(attribute.__value__)
        #return value  # TODO: Which one to return? Default or None?
        return final_value

    def get_negated(self, value):
        """ Returns actual boolean for grammar fillers for negation, "yes"/"no". """
        if value == "yes":
            return True
        return False

    def get_scaleDescriptor(self, scale):
        """ Returns a scaleDescriptor, with unit type, the actual value, and the associated property. """
        return {'units': scale.extras.quantity.units.type(), 'value': float(scale.extras.quantity.amount.value), 'property': scale.extras.quantity.property.type()}

    def get_property(self, pm):
        """ Returns the relevant property values for a PropertyModifier. """
        returned = {}
        kind = pm.kind.type()
        if hasattr(pm, "modifier") and pm.modifier.has_filler():
            filler = {'modifier': self.fill_value("modifier", {"parameters": "modifier"}, pm)}
            returned.update(filler)
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
        return returned


    def get_state(self, eventProcess):
        """ Returns the state for a Stasis Process. """
        predication = {}
        state = eventProcess.state
        predication['negated'] = False
        if state.type():
            if hasattr(state, "negated") and state.negated.type():
                predication['negated'] = self.get_negated(state.negated.type())
            if self.analyzer.issubtype("SCHEMA", state.type(), "ComparativeAdjModifier"):
                predication['base'] = self.get_objectDescriptor(state.base)
                predication.update(self.get_property(state))
                #predication['ground'] = self.get_objectDescriptor(state.ground)
            elif self.analyzer.issubtype("SCHEMA", state.type(), "PropertyModifier"):
                predication.update(self.get_property(state))
                self.check_compatibility(predication)
            elif self.analyzer.issubtype("SCHEMA", state.type(), "RD"):
                predication['amount'] = self.get_scaleDescriptor(state)
                self.check_compatibility(predication['amount'])
            elif self.analyzer.issubtype("SCHEMA", state.type(), "TrajectorLandmark"):
                predication['relation']= self.get_locationDescriptor(state.profiledArea)
                predication['objectDescriptor'] = self.get_objectDescriptor(state.landmark)
            elif self.analyzer.issubtype('SCHEMA', state.type(), 'RefIdentity'):
                predication['identical']= {'objectDescriptor': self.get_objectDescriptor(state.second)}
        return predication

    def check_compatibility(self, predication):
        """ Checks that a protagonist is compatible with some predication, e.g. "the weight of the box is 2 pounds / red*". """
        if self.protagonist and "property" in self.protagonist['objectDescriptor']:
            prop1, prop2  = predication['property'], self.protagonist['objectDescriptor']['property']['objectDescriptor']['type']
            if not self.is_compatible('ONTOLOGY', prop1, prop2):
                raise Exception("Problem with analysis: the predication '{}' is not compatible with '{}'".format(prop1, prop2))

    def get_spgDescriptor(self, spg):
        """ Returns spgDescriptor, with fillers for source, path, and goal. """
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
        """ returns actual SPG value. """
        final = {}
        value = getattr(spg, valueType)
        if value.ontological_category.type() == "location":
            return {'location': (float(value.xCoord), float(value.xCoord))}
        #if value.index() == spg.landmark.index():
        #    od = self.get_objectDescriptor(value)
        #    self._stacked.append({'objectDescriptor': od})
        #    return {'objectDescriptor': od}
        if value.type() == "RD":# and value.ontological_category.type() == "region":
            #return {'objectDescriptor': self.get_objectDescriptor(spg.landmark)}
            od = self.get_objectDescriptor(value)
            self._stacked.append({'objectDescriptor': od})
            return {'objectDescriptor': od}

        return final


    def get_processFeatures(self, p_features):
        """ returns process features from p_features descriptor template.  """
        features = self.descriptor_templates['processFeatures']
        final = {}
        for k, v in features.items():
            if k in p_features.__dir__():
                value = getattr(p_features, v).type()
                if k=="negated":
                    final[k] = self.get_negated(value)
                else:
                    final[k] = value
        return final

    def get_eventFeatures(self, e_features):
        """ returns event features from e_features descriptor template.  """
        features = self.descriptor_templates['eventFeatures']
        final = {}
        for k, v in features.items():
            if k in e_features.__dir__():
                value_filler = getattr(e_features, v)
                value = value_filler.type()
                if k == "negated":
                    final[k] = self.get_negated(value)
                elif k == "duration":
                    #TODO: Do this more generally, or in a cleaner way?
                    final[k] = {'timeUnits': value_filler.timeUnits.type(), 'length': float(value_filler.length.value)}
                else:
                    final[k] = value
        return final

    def get_relationDescriptor(self, relation):
        """ Returns a relation descriptor, describing in a high-level way the relation between several entities. 
        The Problem Solver then uses the relation in the application domain's context to determine the actual meaning. """
        returned = dict()
        template = self.descriptor_templates["relationDescriptor"] if "relationDescriptor" in self.descriptor_templates else dict()
        for k, v in template.items():
            #if hasattr(relation, v) and getattr(relation, v).has_filler():
            print(k)
            value = self.fill_value(k, v, relation)
            #print(value)
            if value:
                returned[k] = value
        return returned

    def get_conjRDDescriptor(self, item, resolving=False):
        """ Returns a data structure for a ConjRD, such as "the man and the woman". """
        return dict(conj=True,
                    first=self.get_objectDescriptor(item.rd1),
                    second=self.get_objectDescriptor(item.rd2))



    def get_objectDescriptor(self, item, resolving=False):
        """ Returns an object descriptor from descriptor template. Uses RD elements, as well as other things pointing to object. """
        returned = {}
        if "pointers" not in item.__dir__():
            item.pointers = self.invert_pointers(item)
        if self.analyzer.issubtype("SCHEMA", item.type(), "ConjRD"):
            returned = self.get_conjRDDescriptor(item, resolving)

        template = self.descriptor_templates['objectDescriptor'] if "objectDescriptor" in self.descriptor_templates else dict()
        allowed_pointers = template['pointers'] if 'pointers' in template else []
        
        for k, v in template.items():
            if k not in ["pointers", "description"] and hasattr(item, v):# and getattr(item, v).type():
                attribute = getattr(item, v).type()
                if attribute:
                    returned[k] = attribute
        if hasattr(item, "extras"):
            returned.update(self.get_RDExtras(item.extras))
        for pointer, mods in item.pointers.items():
            if pointer in allowed_pointers:
                for mod in mods:
                    filler = self.fill_pointer(mod, item)
                    if filler:
                        returned.update(filler)
                        if "property" in filler:
                            if self.protagonist is not None:
                                if not "type" in self.protagonist["objectDescriptor"]:
                                    self.protagonist["objectDescriptor"].update(
                                        filler["property"]["objectDescriptor"])
        if 'referent' in returned:
            if returned['referent'] == "antecedent":
                return self.resolve_referents(returned)['objectDescriptor']
            elif item.referent.type() == "anaphora" and not resolving:
                return self.resolve_anaphoricOne(item)['objectDescriptor']
        return returned


    def get_RDExtras(self, extras):
        """ RD Extras contain embedded RD information, like specificWh, Event-description, quantity. """
        template = self.descriptor_templates['RDExtras']
        returned = {}
        for key, value in template.items():
            #if hasattr(extras, value):
            final = self.fill_value(key, value, extras)
            if final:
                returned[key] = final
        return returned


    def get_eventRDDescriptor(self, item):
        """ Event RDs have an associated event description. """
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
        """ Fills pointers to an RD in a structured way. """
        if hasattr(pointer, "modifiedThing") and pointer.modifiedThing.index() != item.index():
            return None
        elif hasattr(pointer, "temporality") and pointer.temporality.type() != "atemporal":
            return None
        elif hasattr(pointer, "trajector") and pointer.trajector.index() != item.index():
            return None
        elif hasattr(pointer, "possessed") and pointer.possessed.index() != item.index():
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
            elif self.analyzer.issubtype("SCHEMA", pointer.type(), "NounNounModifier") and pointer.modifier.has_filler():
                return dict(modifier=dict(objectDescriptor=self.get_objectDescriptor(pointer.modifier)))
            elif self.analyzer.issubtype("SCHEMA", pointer.type(), "Modification") and pointer.modifier.has_filler():
                return dict(property=dict(objectDescriptor=self.get_objectDescriptor(pointer.modifier)))
            elif self.analyzer.issubtype("SCHEMA", pointer.type(), "RefIdentity") and pointer.second.index() != item.index():
                return dict(identical=dict(objectDescriptor=self.get_objectDescriptor(pointer.second)))
            elif self.analyzer.issubtype("SCHEMA", pointer.type(), "PartWhole") and item.index() != pointer.whole.index():
                return dict(whole=dict(objectDescriptor=self.get_objectDescriptor(pointer.whole)))
            elif self.analyzer.issubtype("SCHEMA", pointer.type(), "Possession"): # and item.index() != pointer.possessor.index():
                return dict(possessor=dict(objectDescriptor=self.get_objectDescriptor(pointer.possessor)))
            elif self.analyzer.issubtype("SCHEMA", pointer.type(), "Relation") and pointer.entity1.index() == item.index():
                return dict(relationDescriptor=self.get_relationDescriptor(pointer))


    def get_processDescriptor(self, process, referent):
        """ Retrieves information about a process, according to existing templates. Meant to be implemented
        in specific extensions of this interface.

        Can be overwritten as needed -- here, it calls the params_for_compound to gather essentially an embedded n-tuple.
        """
        return self.fill_parameters(process)




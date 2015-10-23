"""
module author: Sean Trott <seantrott@icsi.berkeley.edu>

The Core Specializer performs some basic operations in converting a SemSpec to an n-tuple.

"""

from nluas.language.specializer_utils import *
from nluas.utils import *
import pickle
import json


class CoreSpecializer(TemplateSpecializer, UtilitySpecializer):

    def __init__(self, analyzer):

        UtilitySpecializer.__init__(self, analyzer)
        TemplateSpecializer.__init__(self)

        self.simple_processes = {'MotionPath': self.params_for_motionPath,
                                 'Stasis': self.params_for_stasis,
                                 'ForceApplication': self.params_for_forceapplication,
                                 'StagedProcess': self.params_for_stagedprocess}

        self.complex_processes = ['CauseEffect', 'SerialProcess']

        self.moods = {'YN_Question': self.construct_YN,
                     'WH_Question': self.construct_WH,
                     'Declarative': self.construct_Declarative,
                     'Imperative': self.construct_Imperative,
                     'Conditional_Imperative': self.construct_condImp,
                     "Conditional_Declarative": self.construct_condDeclarative
                     }

        self.eventProcess = None
        self.fs = None
        self.core = None

        self.parameters = []


    def read_templates(self, filename):
        with open(filename, "r") as data_file:
            data = json.loads(data_file.read())
            for name, template in data['templates'].items():
                self.__dict__[name] = template

    def get_goal(self, process, params):
        """ Returns an object descriptor of the goal; used for SPG schemas, like in MotionPath."""
        g = process.goal
        goal = dict()
        if g.type() == 'home':
            goal['location'] = g.type()
        elif g.ontological_category.type() == 'heading':
            goal = None
            params.update(heading=g.tag.type())
        elif self.analyzer.issubtype('ONTOLOGY', g.ontological_category.type(), 'part'): # checks if it's a "part" in a part whole relation
            goal['partDescriptor'] = {'objectDescriptor': self.get_objectDescriptor(g.extensions.whole), 'relation': self.get_objectDescriptor(g)}    
        elif g.ontological_category.type() == 'region':
            goal['locationDescriptor'] = {'objectDescriptor': self.get_objectDescriptor(process.landmark), 'relation': self.get_locationDescriptor(g)}  
        elif g.referent.type() == 'anaphora':
            try:
                goal = self.resolve_anaphoricOne(g)
            except ReferentResolutionException as e:
                print(e.message)
        elif g.referent.type():
            if g.referent.type() == "antecedent":
                try:
                    if g.givenness.type() == 'distinct':
                        goal = self.resolve_anaphoricOne(g)
                    else:
                        goal = self.resolve_referents(params['action'])
                except ReferentResolutionException as e:
                    print(e.message)
                    return None
                # Resolve_referents()
            else:
                goal['objectDescriptor'] = self.get_objectDescriptor(g) #{'referent': g.referent.type(), 'type': g.ontological_category.type()}    ## Possibly add "object descriptor" as key here        
        elif g.ontological_category.type() == 'location':
            # if complex location, get "location descriptor"
            goal['location'] = (int(g.xCoord), int(g.yCoord))
        else:
            goal['objectDescriptor'] = self.get_objectDescriptor(g) #properties
            #goal.objectDescriptor['type'] = goal.type
        self._stacked.append(goal)
        return goal   

    def get_protagonist(self, protagonist, process):
        """ Returns the protagonist of PROCESS. Checks to see what kind of referent / object it is. """
        pro = protagonist
        if pro.type() == "ConjRD":
            p1 = self.get_protagonist(pro.rd1, process)
            p2 = self.get_protagonist(pro.rd2, process)
            subject = {'objectDescriptor': {'referent': 'joint', 'joint': {'first': p1, 'second': p2}}}
        elif protagonist.referent.type() == 'anaphora':
            try:
                subject = self.resolve_anaphoricOne(protagonist)
            except ReferentResolutionException as e:
                print(e.message)
        elif hasattr(protagonist, 'referent') and protagonist.referent.type() == "antecedent":
            try:
                subject = self.resolve_referents(self.get_actionary(process))
            except ReferentResolutionException as e:
                print(e.message)
                return None
        else:
            if not hasattr(protagonist, "referent"):
                subject = {'objectDescriptor': {'referent': 'unknown'}}
            else:
                subject = {'objectDescriptor': self.get_objectDescriptor(protagonist)}
                if subject['objectDescriptor']['type'] != 'robot':
                    self._stacked.append(subject)
        return subject

    def get_actionary(self, process):
        """ Returns the actionary of PROCESS. Checks to make sure actionary is contained in process. """
        if hasattr(process, "actionary"):
            v = process.actionary.type()
            return v
        elif process.type() == 'MotionPath':
           return 'move'
        return None

    # Returns parameters for Stasis type of process ("the box is red")
    def params_for_stasis(self, process, params):
        prop = process.state
        a = {}
        a['negated'] = False
        if "negated" in prop.__dir__() and prop.negated.type() == "yes":
            a['negated'] = True
        #params = updated(d, action = process.actionary.type()) #process.protagonist.ontological_category.type())
        if self.analyzer.issubtype('SCHEMA', prop.type(), 'PropertyModifier'):
            a[str(prop.property.type())] = prop.value.type()#, 'type': 'property'}
            if hasattr(prop, 'kind') and prop.kind:
                a['kind'] = prop.kind.type()
                if a['kind'] == "comparative" and self.analyzer.issubtype("SCHEMA", prop.type(), "ComparativeAdjModifier"):
                    a['base'] = {'objectDescriptor': self.get_objectDescriptor(prop.base)}
        elif self.analyzer.issubtype('SCHEMA', prop.type(), 'RefIdentity'):
            a['identical']= {'objectDescriptor': self.get_objectDescriptor(prop.second)}
            params.update(predication = a)
        elif self.analyzer.issubtype('SCHEMA', prop.type(), 'QuantifiedRD'):
            a['quantity'] = dict(units=prop.units.type(),
                                 amount=float(prop.amount.value))
        elif self.analyzer.issubtype('SCHEMA', prop.type(), 'TrajectorLandmark'):
            if prop.landmark.referent.type() == 'antecedent':
                landmark = get_referent(process, params)
            else:
                landmark = self.get_objectDescriptor(prop.landmark)
            a['relation']= self.get_locationDescriptor(prop.profiledArea) 
            a['objectDescriptor']= landmark
            #print(prop.profiledArea.ontological_category.type())
            params.update(predication=a)
        #if not 'specificWh' in params:  # Check if it's a WH question, in which case we don't want to do "X-check"
        #    params = self.crosscheck_params(params)

        params.update(predication = a)
        return params                


    
    def params_for_motionPath(self, process, params):
        """ returns parameters for motion path process ("move to the box"). """
        s = self.get_actionDescriptor(process)
        if 'collaborative' in s:
            params.update(collaborative=s['collaborative'])
        if 'speed' in s and s['speed'] is not None:
            params.update(speed = float(s['speed']))
        if hasattr(process, 'heading'):
            if process.heading.type():
                params.update(heading=process.heading.tag.type())
        # Is a distance specified?                
        if hasattr(process.spg, 'distance') and hasattr(process.spg.distance, 'amount'):
            d = process.spg.distance
            params.update(distance={"value": float(d.amount.value), "units":d.units.type()})
        # Is a goal specified?
        if hasattr(process.spg, 'goal'):
            params.update(goal = self.get_goal(process.spg, params))
        if hasattr(process, 'direction'):
            params.update(direction=process.direction.type())              
        return params   

    # gets params for force-application, like "push the box"
    def params_for_forceapplication(self, process, params):
        """ Gets params for Force Application process. """
        affected = self.get_protagonist(process.actedUpon, process)
        params.update(acted_upon=affected)
        return params   

    def params_for_stagedprocess(self,process, d):
        params = updated(self._execute, 
                         action=self.core.m.profiledProcess.actionary.type(), 
                         protagonist={'objectDescriptor': self.get_objectDescriptor(process.protagonist)})
        if self.eventProcess.stageRole.type():
            params.update(control_state=self.eventProcess.stageRole.type())
        return params  

    def causalProcess(self, process, param_name="_execute"):

        params = updated(self._cause, action = process.actionary.type())
        params.update(causer = self.get_protagonist(process.protagonist, process))
        params.update(protagonist = params['causer'])
        collab = self.get_actionDescriptor(process)
        if 'collaborative' in collab:
            params.update(collaborative=collab['collaborative'])
        if "joint" in params['causer']['objectDescriptor']:
            params.update(collaborative=True)
        if hasattr(process, "p_features"):
            params = updated(params, p_features=self.get_process_features(process.p_features))
        param_type = getattr(self, param_name)
        cp = self.params_for_simple(process.process1, param_type)
        ap = self.params_for_simple(process.process2, param_type)
        params.update(causalProcess = cp)
        params.update(affectedProcess = ap)
        return params

    def process_is_subtype(self, process):
        for p in self.simple_processes:
            if self.analyzer.issubtype('SCHEMA', process.type(), p):
                return p 
        return False

    # This function just returns params for "where", like "where is Box1". Different process format than "which box is red?"
    def params_for_where(self, process, d):
        params = updated(d, action=process.actionary.type())
        h = process.state.second
        params.update(protagonist=self.get_protagonist(h, process))
        return params

    # Dispatches "process" to a function to fill in template, depending on process type. Returns parameters.
    def params_for_simple(self, process, template):
        if template == self._WH:
            if hasattr(process.protagonist, "specificWh"):
                template['specificWh'] = process.protagonist.specificWh.type()
                if template['specificWh'] == "where":
                    return self.params_for_where(process, template)

        params = updated(template, action = self.get_actionary(process))

        if hasattr(process, "protagonist"):
            params = updated(params, protagonist=self.get_protagonist(process.protagonist, process))

        if hasattr(process, "p_features"):
            params = updated(params, p_features=self.get_process_features(process.p_features))
        if not process.type() in self.simple_processes:
            if self.process_is_subtype(process):
                return self.simple_processes[sub](process, params)
            return self.params_for_undefined_process(process, params)

        #assert process.type() in self.simple_processes, 'problem: process type {} not in allowed types'.format(process.type())
        return self.simple_processes[process.type()](process, params)

    def params_for_undefined_process(self, process, params):
        return params



    def get_process_features(self, p_features):
        features = dict()
        for role, filler in p_features.__items__():
            if filler:
                features[str(role)] = filler.type()
        return features

    def params_for_compound(self, process, param_name="_execute"):
        if process.type() == 'SerialProcess':
            for pgen in chain(map(self.params_for_compound, (process.process1, process.process2))):
                for p in pgen:
                    if p is None:
                        None
                    else:
                        yield p
        elif self.analyzer.issubtype("SCHEMA", process.type(), "CauseEffect"):
            yield self.causalProcess(process, param_name)
        elif process.type() == 'CauseEffectProcess':
            yield self.causalProcess(process, param_name)
        else:
            params = getattr(self, param_name)
            yield self.params_for_simple(process, params)  # EXECUTE is default 
    
    def make_parameters(self, fs):
        # Add mood for conditionals, etc.        
        mood = fs.m.mood.replace('-', '_')
        #assert mood in ('YN_Question', 'WH_Question', 'Declarative', 'Imperative', 'Conditional_Imperative', 'Definition')

        assert mood in list(self.moods.keys())

        self.needs_solve = True
        self.core = fs.rootconstituent.core 

        self.eventProcess = self.core.m.eventProcess
        return self.moods[mood]()

    def construct_YN(self):
        params = list(self.params_for_compound(self.eventProcess, "_YN"))
        return params 

    def construct_WH(self):
        params = list(self.params_for_compound(self.eventProcess, "_WH"))
        return params

    def construct_Declarative(self):
        params = list(self.params_for_compound(self.eventProcess, "_assertion"))
        return params

    def construct_condImp(self):
        cond = list(self.params_for_compound(self.core.m.ed1.eventProcess, "_YN")) # Changed so that condition can be compound / cause ("If you pushed the box North, then move box1 then move box2...")
        params = updated(self._YN)
        action = list(self.params_for_compound(self.core.m.ed2.eventProcess)) #params_for_compound(core.m.ed1.eventProcess)
        action2 = []
        cond2 = []
        if cond is None or None in action:
            return None
        for i in action:
            action2.append(i)
        for i in cond:
            cond2.append(i) 
        params = [updated(self._conditional_imperative, command=action2, condition=cond2)]
        return params 


    def construct_condDeclarative(self):
        cond = list(self.params_for_compound(self.core.m.ed1.eventProcess, "_YN")) # Changed so that condition can be compound / cause ("If you pushed the box North, then move box1 then move box2...")
        params = updated(self._YN)
        action = list(self.params_for_compound(self.core.m.ed2.eventProcess, "_assertion")) #params_for_compound(core.m.ed1.eventProcess)
        action2 = []
        cond2 = []
        if cond is None or None in action:
            return None
        for i in action:
            action2.append(i)
        for i in cond:
            cond2.append(i) 
        params = [updated(self._conditional_declarative, assertion=action2, condition=cond2)]
        return params   

    def construct_Imperative(self):
        t = self.eventProcess.type()
        allowed_types = dict(compound=self.complex_processes,
                             simple=list(self.simple_processes.keys()))
        assert t in flatten(allowed_types.values()), 'problem: process type is: %s' % t
        if t in allowed_types['simple']:
            return [self.params_for_simple(self.eventProcess, self._execute)]
        else:
            return list(self.params_for_compound(self.eventProcess))  


    def specialize(self, fs):
        """This method takes a SemSpec (the fs parameter) and outputs an n-tuple.
        """
        self.fs = fs
        mood = fs.m.mood.replace('-', '_')

        # Dispatch call to some other specialize_* methods.
        # Note: now parameters is a sequence.
        params = self.make_parameters(fs)

        if params is None or params[0] is None:
            self.needs_solve == False
            return None

        params = [self.replace_mappings(param) for param in params]

        ntuple = updated(self._wrapper,
                         getattr(self, 'specialize_%s' % mood)(fs),
                         parameters=params) #[Struct(param) for param in params])


        self.parameters += params

        if self.debug_mode:
            print(ntuple)
            #dumpfile = open('src/main/pickled.p', 'ab')
            #pickle.dump(Struct(ntuple), dumpfile)
            #dumpfile.close()
            #dumpfile2 = open('src/main/move')
            #self._output.write("\n\n{0} \n{1} \n{2}".format(mood, self._sentence, str(Struct(ntuple))))
        return ntuple 
        #return Struct(ntuple)

    def specialize_Conditional_Declarative(self, fs):
        return dict(predicate_type='conditional_declarative', return_type = 'error_descriptor')   

    def specialize_Conditional_Imperative(self, fs):
        return dict(predicate_type='conditional_imperative', return_type = 'error_descriptor')    

    def specialize_YN_Question(self, fs):
        return dict(predicate_type='query', return_type='boolean')

    def specialize_WH_Question(self, fs):
        specific = fs.m.content.profiledParticipant.specificWh.type()
        f = 'collection_of' if fs.m.content.profiledParticipant.number.type() == 'plural' else 'singleton'
        return dict(predicate_type='query',
                    return_type='%s::class_reference' % f if specific == 'what' else '%s::instance_reference' % f)

    def specialize_Declarative(self, fs):
        return dict(predicate_type='assertion', return_type='error_descriptor')

    def specialize_Imperative(self, fs):
        return dict(predicate_type='command', return_type='error_descriptor')

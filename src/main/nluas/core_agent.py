"""
Author: seantrott <seantrott@icsi.berkeley.edu>

Defines a CoreAgent, which uses the Transport module. Can be initialized
by just feeding it a channel name. All "Agents" inherit from the CoreAgent. 

------
See LICENSE.txt for licensing information.
------
"""

from nluas.Transport import *
import argparse
import os
import sys
import logging

from collections import OrderedDict


class CoreAgent(object):

    def __init__(self, params):
        self.parser = self.setup_parser()
        args = self.parser.parse_known_args(params)
        self.unknown = args[1]
        self.setup_federation()
        self.initialize(args[0])

    def read_templates(self, filename):
        """ Sets each template to ordered dict."""
        #print("Parsing " + filename)
        base = OrderedDict()
        # Add basic information from templates
        with open(filename, "r") as data_file:
            #data = json.loads(data_file.read())
            data = json.load(data_file, object_pairs_hook=OrderedDict)
            for name, template in data['templates'].items():
                setattr(self, name, template)
                base[name] = template
        # Add information from parents for each template
        # Overriding rules: choose child key/value pair if key is in both child and parent
        for name, template in base.items():
            if "parents" in template:
                for parent in template['parents']:
                    if parent in base:
                        template = self.unify_templates(template, base[parent])
                    else:
                        raise Exception("issue")
                        # Throw exception
                template.pop("parents")
        return base

    def unify_templates(self, child, parent):
        """ Unifies a child and parent template. Adds all parent key-value pairs 
        unless the key already exists in the child. """
        child.update({key:value for (key, value) in parent.items() if key not in child})
        return child

    def setup_federation(self):
        self.federation = os.environ.get("ECG_FED")
        if self.federation is None:
            self.federation = "FED1"

    def initialize(self, args):
        self.name = args.name
        self.address = "{}_{}".format(self.federation, self.name)
        self.transport = Transport(self.address)
        self.logfile = args.logfile
        self.loglevel = args.loglevel
        self.logagent = args.logagent

    def setup_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("name", type=str, help="assign a name to this agent")
        parser.add_argument("-logfile", type=str, help="indicate logfile path for logging output")
        parser.add_argument("-loglevel", type=str, help="indicate loglevel for logging output: warn, debug, error")
        parser.add_argument("-logagent", type=str, help="indicate agent responsible for logging output")
        return parser

    def close(self):
        #self.transport.join()
        print("Transport needs a QUIT procedure.")
        sys.exit()


    def callback(self, ntuple):
        print("{} received {}.".format(self.name, ntuple))

    def subscribe_mass(self, ports):
        for port in ports:
            self.transport.subscribe(port, self.callback)



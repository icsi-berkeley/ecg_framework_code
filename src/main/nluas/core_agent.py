"""
Author: seantrott <seantrott@icsi.berkeley.edu>
"""

from nluas.Transport import *
import argparse
import os
import sys
import logging


class CoreAgent(object):

    def __init__(self, params):
        self.parser = self.setup_parser()
        args = self.parser.parse_known_args(params)
        self.unknown = args[1]
        self.setup_federation()
        self.initialize(args[0])

    def read_templates(self, filename):
        with open(filename, "r") as data_file:
            data = json.loads(data_file.read())
            for name, template in data['templates'].items():
                self.__dict__[name] = template

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



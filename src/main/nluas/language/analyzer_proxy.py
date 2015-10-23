""" Proxy for Analyzer. Used by "main" to connect with Analyzer object.

Author: seantrott <seantrott@icsi.berkeley.edu>

"""
try:
    # Python 2?
    from xmlrpclib import ServerProxy, Fault  # @UnresolvedImport @UnusedImport
except:
    # Therefore it must be Python 3.
    from xmlrpc.client import ServerProxy, Fault

from nluas.feature import StructJSONEncoder, as_featurestruct
import os

class Analyzer(object):
    """A proxy for the Analyzer. 
    Note: It assumes the server is running with the right grammar
    """
    def __init__(self, url):
        self.analyzer = ServerProxy(url, encoding='utf-8') 
        
    def parse(self, sentence):        
        return [as_featurestruct(r, s) for r, s in self.analyzer.parse(sentence)]
    
    def issubtype(self, typesystem, child, parent):
        return self.analyzer.issubtype(typesystem, child, parent)

    def get_mapping_path(self):
        return os.path.realpath(self.analyzer.get_mapping())

    def get_mappings(self):
        return self.analyzer.get_mappings()

    def get_lexicon(self):
        return self.analyzer.get_lexicon()

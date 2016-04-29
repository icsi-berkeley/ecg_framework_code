""" Proxy for Analyzer. Used by "main" to connect with Analyzer object.

Author: seantrott <seantrott@icsi.berkeley.edu>

------
See LICENSE.txt for licensing information.
------

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
        total = self.analyzer.parse(sentence)
        parse = total['parse']
        spans = total['spans']

        return [as_featurestruct(r, s) for r, s in parse]

    def full_parse(self, sentence):
        total = self.analyzer.parse(sentence)
        parse = [as_featurestruct(r, s) for r, s in total['parse']]
        spans = total['spans']
        return {'spans': spans, 'parse': parse, 'original': total['parse'], 'costs':total['costs']}
    
    def issubtype(self, typesystem, child, parent):
        return self.analyzer.issubtype(typesystem, child, parent)

    def get_mapping_path(self):
        return os.path.realpath(self.analyzer.get_mapping())

    def get_mappings(self):
        return self.analyzer.get_mappings()

    def get_lexicon(self):
        return self.analyzer.get_lexicon()

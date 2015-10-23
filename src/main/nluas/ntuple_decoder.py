from pprint import pprint
from json import dumps, loads
from nluas.feature import StructJSONEncoder
from nluas.utils import Struct

class Color(object):
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

class NtupleDecoder(object):
	def __init__(self):
		self.ntuple = None

	def convert_to_JSON(self, ntuple):
		json_ntuple = dumps(ntuple, cls=StructJSONEncoder, indent=2)
		return json_ntuple


	def convert_JSON_to_ntuple(self, json_ntuple):
		ntuple = loads(json_ntuple, object_hook=StructJSONEncoder.as_struct)
		return ntuple


	def pprint_ntuple(self, ntuple):
		print("{}Predicate type {}: {}".format(Color.BOLD, Color.END, ntuple['predicate_type']))
		print("{}Return type {}: {}".format(Color.BOLD, Color.END, ntuple['return_type']))
		for param in ntuple['parameters']:
			for key, value in param.items():
				if value:
					print("{}{}{}: {}".format(Color.BOLD, key, Color.END, value))
		print("\n")
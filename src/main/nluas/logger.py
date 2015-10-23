"""
A simple module that receives logging information and prints it.

A UserAgent controls a LoggingAgent, which logs messages.

How should this be implemented? 
"""

import logging
from nluas.Transport import Transport

class LoggingAgent(object):
	def __init__(self, federation):
		self._prefix = federation
		self._receiver = Transport("{}_Logger".format(self._prefix))


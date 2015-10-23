#!/usr/bin/env python
######################################################################
#
# File: Transport.py
#
# Initial Version: July 13, 2015 Adam Janin
#
# TODO:
#
# Figure out what to do if you try to send a message and nobody's listening.
#
# Add TransportWarning exception for stuff that should be safely ignorable.
#
# Maybe multiple subscribes should be allowed? Currently, setting up
# a second subscribe to the same port throws an exception.
#
# Changes:
#

# NOTES:
#
# To enable logging just from Transport and not also from e.g. Pyre
# itself, you'll need a specialized channel. In your main:
# logger = logging.getLogger('Transport')
# ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)
# logger.setLevel(logging.DEBUG)
# logger.addHandler(ch)
#
# Pyre.set_port() is broken in the current Pyre implementation. If
# you want to do multiple federations, use e.g.:
# t = Transport(name, prefix='foo')

import collections
import datetime
import inspect
import ipaddress
import json
import logging
import os
import re
import sys
import threading
import uuid

from pyre import Pyre
import zmq

VERSION = 0.1

logger = logging.getLogger('Transport')

def is_valid_ip(ipstr):
    '''Return true if the IP address is acceptable. Currently, acceptable addresses are loopback (e.g. localhost), non-routables (e.g. 192.68.0.1), or within ICSI (e.g. 192.150.186.135)'''

    ip=ipaddress.ip_address(ipstr)

    return ip.is_loopback or ip.is_private or ip in ipaddress.ip_network('192.150.186.0/24')
# is_valid_ip()

# Base class for exceptions from a Transport. Should probably also
# have TransportWarning since many of the errors could be safely
# ignored.

class TransportError(Exception):
    '''Base class for exceptions associated with a Transport.'''
    def __init__(self, t, m):
        self.transport = t
        self.msg = m
    # __init__()
    def __str__(self):
        if self.transport is not None and self.transport._pyre is not None:
            return 'Transport %s %s: %s'%(self.transport._pyre.uuid(), self.transport._pyre.name(), self.msg)
        else:
            return 'Uninitialized Transport: %s'%(self.msg)
    # __str__()
# class TransportError

class TransportProtocolError(TransportError):
    '''Raised if an unexpected for malformed message is received'''
    pass

class TransportSecurityError(TransportError):
    '''Raised if a sender's IP address isn't valid according to Transport.is_valid_ip()'''
    pass

######################################################################
#
# The main class for Transport. On creation, sets up a thread to
# listen for incoming messages. 
#

class Transport():
    '''Message transport mechanisms for LCAS'''

    def send(self, dest, ntuple):
        '''Send given ntuple to Transport named dest. If dest isn't listening for messages from this Transport, the message will (currently) be silently ignored.'''
        if self._prefix is not None:
            dest = self._prefix + dest
        self._pyre.shout(dest, json.dumps(ntuple).encode('utf-8'))
    # send()

    # Notes on subscribe
    #
    # The callback is called in the same thread that listens for pyre
    # messages, so the callback should start a new thread if it's
    # going to block or take a long time to run.
    #
    # The callback must take one positional argument, the tuple, and
    # can OPTIONALLY take a keyword argument (e.g. **kw). I use the
    # inspect module to detect this. May be too clever for my own
    # good.
    #
    # There can be only one callback for a given remote. If you call
    # subscribe again with the same remote, it raises an error.

    def subscribe(self, remote, callback):
        '''When a message is sent from a Transport named remote to this transport, call the passed callback with the ntuple as the first argument. If the callback takes **kw, it will also pass additional metadata such as the Transport name, UUID, and IP of the sender.'''
        if self._prefix is not None:
            remote = self._prefix + remote
        if remote in self._subscribers:
            raise TransportError(self, 'Transport.subscribe() was called a second time with the same remote (\"%s\"). You must call Transport.unsubscribe() before setting a new callback.'%(remote))
        self._subscribers[remote] = callback
    # subscribe()

    def unsubscribe(self, remote):
        '''Stop listening for messages from remote.'''
        if self._prefix is not None:
            remote = self._prefix + remote
        if remote in self._subscribers:
            del self._subscribers[remote]
    # unsubscribe()

    def subscribe_all(self, callback):
        '''Call callback every time a message is sent from any remote Transport to this Transport.'''
        if self._subscribe_all is not None:
            raise TransportError(self, 'Transport.subscribe_all() was called a second time. You must call Transport.unsubscribe_all() before setting a new callback.')
        self._subscribe_all = callback
    # subscribe_all()

    def unsubscribe_all(self):
        self._subscribe_all = None
    # unsubscribe_all()

    # Notes on get()
    #    
    # If you already subscribe to remote, temporarly overrides
    # the subscribe. The subscribed callback will NOT be called.
    # The subscription is replaced after get() returns.

    def get(self, remote):
        '''Block waiting for a message from a Transport named remote. Returns python namedtuple containing fields object, uuid, name, ip, datetime.'''

        if self._prefix is not None:
            remote = self._prefix + remote

        # The final python namedtuple to be returned gets stored in ret
        ret = None

        # The event e will get set when a message is read by the
        # readthread.
        e = threading.Event()

        # This function is a callback used to detect the next message.
        # It stores the message in a Python namedtuple and sets the
        # event.

        def get_callback(tup, **kw):
            nonlocal ret, e
            ret = collections.namedtuple('TransportEnvelope', ['object', 'uuid', 'name', 'ip', 'datetime'])(tup, kw['uuid'], kw['name'], kw['ip'], kw['datetime'])
            # Inform get() that ret is ready to be returned.
            e.set()
        # get_callback()

        # Store the old callback, if any
        oldcb = self._subscribers.get(remote, None)

        # Set the subscription
        self._subscribers[remote] = get_callback
        
        # Wait for the callback to be called.
        e.wait()

        # Restore the old subscription, if any.
        if oldcb is not None:
            self._subscribers[remote] = oldcb
        else:
            del self._subscribers[remote]

        # Return the namedtuple.
        return ret
    # get()

    def quit_federation(self):
        '''Send a quit message to all agents in this federation, and then close down the Transport.'''
        self._pyre.shouts(self._globalchannel, u"QUIT")
        self._run = False
        # Wait for the readthread to finish
        self._readthread.join()
        # Tell Pyre to shut down
        self._pyre.stop()

    def is_running(self):
        '''Return the status of this Transport. If the Transport isn't running, you should not send it messages and the callbacks will not be called.'''
        return self._run

    ######################################################################
    # All private methods below here

    def __init__(self, myname, port=None, prefix=None):
        # NOTE: Seems to be a bug in Pyre where you can't set the port.
        if port is not None:
            raise NotImplementedError('There is a bug in Pyre that prevents setting of the discovery port. If you require multiple federations of Pyre components, use prefix instead of port in Transport constructor.')

        # dict of remote name to callback. See subscribe method above.
        self._subscribers = {}
        
        # Callback for all message (or None if none registered)
        self._subscribe_all = None

        self._prefix = prefix

        # Attach the federation name as a prefix to both this channel
        # and the global channel. The global channel is currently
        # just used for QUIT messages.

        if prefix is not None:
            myname = prefix + myname
            self._globalchannel = prefix + "GLOBAL"
        else:
            self._globalchannel = "GLOBAL"

        self._pyre = Pyre(myname)
        if port is not None:
            self._pyre.set_port(port)

        self._pyre.join(myname)
        self._pyre.join(self._globalchannel)
        self._pyre.start()

        # Dict of (UUIDs => IP addresses) that have sent a valid ENTER message
        self._uuid2ip = {}

        self._run = True

        self._readthread = threading.Thread(target=self._readworker)
        self._readthread.start()
    # __init__()

    # Handle pyre messages. Run in self._readthread
    def _readworker(self):
        '''This method is called in a separate thread to handle messages sent over pyre. It dispataches to methods named for the pyre events (e.g. _ENTER).'''

        # Set up a poller so recv doesn't block. Possibly not needed
        # since we'll always get an event when the other agents quit,
        # but just in case something goes wrong, we want to be sure to
        # close down.

        poller = zmq.Poller()
        sock = self._pyre.socket()
        poller.register(sock, zmq.POLLIN)

        while self._run:
            # Wait until a message is received OR one second timeout.
            items = dict(poller.poll(1000))
            if not (sock in items and items[sock] == zmq.POLLIN):
                # This should only happen if we time out.
                continue
            # There's an event waiting. Read and process it.
            event = self._pyre.recv()
            logger.debug('Transport %s-%s received event %s'%(self._pyre.uuid(), self._pyre.name(), event))
            eventtype = event[0].decode('utf-8')
            # Sender's uuid and name
            sid = uuid.UUID(bytes=event[1])
            name = event[2].decode('utf-8')
            # Make sure we've seen matching ENTER for all events
            if eventtype != 'ENTER' and sid not in self._uuid2ip:
                raise TransportProtocolError(self, 'Received event %s with no matching ENTER.'%(event))
                continue

            if eventtype == 'ENTER':
                # Changed
                url = event[3].decode('utf-8')
                self._ENTER(sid, name, url)
            elif eventtype == 'JOIN':
                channel = event[3].decode('utf-8')
                self._JOIN(sid, name, channel)
            elif eventtype == 'SHOUT':
                channel = event[3].decode('utf-8')
                message = event[4].decode('utf-8')
                if channel == self._globalchannel and message == "QUIT":
                    # Set ourself to stop running, close down pyre, exit
                    # worker thread.
                    self._run = False
                    self._pyre.stop()
                    break
                else:
                    self._SHOUT(sid, name, channel, message)
            elif eventtype == 'WHISPER':
                message = event[3].decode('utf-8')
                self._WHISPER(sid, name, message)
            elif eventtype == 'LEAVE':
                channel = event[3].decode('utf-8')
                self._LEAVE(sid, name, channel)
            elif eventtype == 'EXIT':
                self._EXIT(sid, name)
            else:
                raise TransportProtocolError(self, 'Illegal event type in event %s'%(event))
    # _readworker()

    # The following methods are named for the pyre event that this
    # instance has received. They are called automatically from the
    # worker thread that's listening for events.

    def _ENTER(self, sid, name, url):
        # We expect all connections to be tcp on some port. This regular
        # expression is used to extract the ip part.
        urlmatch = re.match('tcp://([0-9.]+):[0-9]+$', url)
        if urlmatch:
            ip = urlmatch.group(1)
            if is_valid_ip(ip):
                # Everything looks good. Add to list of valid uuids.
                self._uuid2ip[sid] = ip
            else:
                raise TransportSecurityError(self, 'Message from invalid IP address in ENTER %s %s %s. Check the function is_valid_ip() in Transport.py.'%(sid, name, url))
        else:
            raise TransportProtocolError(self, 'Malformed URL in ENTER %s %s %s'%(sid, name, url))
    # _ENTER()

    def _JOIN(self, sid, name, channel):
        pass
    # _JOIN()

    def _SHOUT(self, sid, name, channel, message):
        now = datetime.datetime.now()
        if name in self._subscribers:
            cb = self._subscribers[name]
            self._call_callback(cb, sid, name, channel, message, now)
        if self._subscribe_all is not None:
            cb = self._subscribe_all
            self._call_callback(cb, sid, name, channel, message, now)
    # _SHOUT()

    def _call_callback(self, cb, sid, name, channel, message, now):
        if inspect.getargspec(cb).keywords is None:
            cb(json.loads(message))
        else:
            cb(message, uuid=sid, name=name, ip=self._uuid2ip[sid], datetime=now)
    # _call_callback


    def _WHISPER(self, sid, name, message):
        raise TransportProtocolError(self, 'Unexpected WHISPER from %s %s'%(sid, name))
    # _WHISPER()

    def _LEAVE(self, sid, name, channel):
        pass
    # _LEAVE()

    def _EXIT(self, sid, name):
        # Remove sid from list of valid uuids. This should
        # never be an error since we check in _readworker().
        del self._uuid2ip[sid]
    # _EXIT()
# class Transport

# minimal chat example
if __name__ == "__main__":
    myname = sys.argv[1]
    remotename = sys.argv[2]

    t = Transport(myname)
    t.subscribe(remotename, lambda tuple: print('Got', tuple))

    while True:
        t.send(remotename, input())

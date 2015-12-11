#!/usr/bin/env python
######################################################################
#
# File: bridge_client.py
# 
# Initial Version: Dec 9, 2015 Adam Janin
#
# Bridge two Transport networks.
#
# BUGS:
# 
# Does not handle federations. 
#
# Does not handle non-Transport pyre communications.
#
# TODO: 
#
# Handle federations. Filter out non-Transport pyre messages.
#
# Handle the case where Transports join/leave dynamically.
#
# Support python3.
#
# Perhaps make multithreaded?

############## How It Works #############
#
# The bridge client firsts creates a socket to communicate with a
# bridge server. Then, the client simultaneously listens on the socket
# and on local pyre (Transport) communications.
#
# When a local pyre client generates a JOIN, LEAVE, or SHOUT message,
# the bridge client will send the fact to the bridge server, which in
# turn sends it to all other bridge clients.
#
# When the bridge client receives a JOIN message from the bridge
# server, it creates a "proxy" Transport object with the same name as
# the remote Transport that sent the JOIN message.
#
# When the bridge client receives a SHOUT message from the bridge
# server, it checks if any local Transport objects are the
# destination. If so, it uses the proxy Transport to send the message
# to the destination Transport.
#
# NOTES:
#
# LEAVE messages are not currently handled since I'm not sure how to
# guarantee that NO remote Transports exist. I guess the server could
# keep track, but I wanted to keep the server really simple.
#
# The client/server communicate with a low level socket, which
# introduces some complexity in the code. Specifically, the objects
# have to be serialized (using json), and we have to handle framing
# ourselves. Framing is done by sending an ascii count of the
# serialized object's size in bytes followed by a newline (\n)
# followed by the bytes in the serialized object.
#

from __future__ import print_function

from six.moves import input
import six

import argparse
import json
import logging
import select
import signal
import socket
import sys
import threading
import uuid

from pyre import Pyre
import zmq

from lcas import Transport

VERSION = 0.1

class Global:
    '''Stores globals. There should be no instances of Global.'''

    # A Pyre object used to listen into local traffic
    pyre = None

    # A socket to the bridge server
    bridgesocket = None

    # Lock objects for interacting with the bridgesocket.
    # Not currently needed, but if performance is an issue,
    # the code could be upgraded to multithread.
    readlock = threading.Lock()
    writelock = threading.Lock()

    # Dict of local channel name -> count of clients on channel.
    # When count goes to 0, the bridge client can leave channel
    localchannelcount = {}

    # Dict of channel name -> Transport object. These are proxy
    # objects for Transports at the other end of the bridge.
    proxies = {}

    # Dict of UUID -> Transport for proxies. Just a faster way
    # to tell if a UUID belongs to a proxy.
    proxy_uuids = {}

    # Command line argument argparse object
    args = None

# end class Globals

def main(argv):

    if six.PY3:
        sys.stderr.write('bridge_client.py currently only supports python2')
        sys.exit(1)

    parse_arguments(argv[1:])
    setup_logging()

    # If the user presses ctrl-C, exit cleanly.
    signal.signal(signal.SIGINT, lambda s, f: client_quit())

    # Create the bridge socket
    Global.bridgesocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    Global.bridgesocket.connect((Global.args.host, Global.args.port))

    # Create a pyre instance
    Global.pyre = Pyre()
    Global.pyre.start()

    # Create a poller object that tests if anything is available on
    # any of: 1) The local pyre channels, 2) The bridge socket, 3) stdin.

    poller = zmq.Poller()
    poller.register(Global.pyre.socket(), zmq.POLLIN)
    poller.register(Global.bridgesocket, zmq.POLLIN)
    poller.register(0, zmq.POLLIN)  # stdin

    logging.warning('Starting bridge client to server at %s:%d'%(Global.args.host, Global.args.port))

    while True:
        items = dict(poller.poll())
        logging.debug('Got items =%s'%(items))

        if 0 in items:  # stdin
            # User typed 'quit'. Note: slightly different from
            # a quit message on the global channel in that this
            # doesn't cause remote to quit.
            message = input()
            if message == 'quit':
                client_quit()
            elif message == 'help':
                print('You can quit the bridge_client (but not the federation) by typing "quit".')
            else:
                print('Unrecognized command %s'%(message))

        if Global.bridgesocket.fileno() in items:
            # Got a message from the remote.
            rec = server_recv()
            logging.debug('Got remote data %s'%(rec))
            if rec[0] == 'JOIN':
                channel = rec[1]
                # If we don't already have a proxy object, create one.
                if channel not in Global.proxies:
                    t = Transport.Transport(channel)
                    Global.pyre.join(channel)
                    Global.proxies[channel] = t
                    Global.proxy_uuids[t._pyre.uuid()] = t
                    logging.info('Creating bridge proxy %s'%(channel))
            elif rec[0] == 'LEAVE':
                # Don't actually know how to handle this.
                pass
            elif rec[0] == 'SHOUT':
                # Use the proxy object to relay the message.
                name = rec[1]
                channel = rec[2]
                message = rec[3]
                if Global.localchannelcount.get(channel, 0) > 0:
                    logging.debug('Bridge proxy shout %s %s %s'%(name, channel, message))
                    Global.proxies[name].send(channel, message)
            else:
                logging.warning('Unexpected msg %s from client.'%(rec))
            
        if Global.pyre.socket() in items:
            # Got a message on Pyre.
            event = Global.pyre.recv()
            logging.debug('Got local pyre event %s'%(event))
            eventtype = event[0].decode('utf-8')
            sid = uuid.UUID(bytes=event[1])
            name = event[2].decode('utf-8')

            # Ignore pyre events from proxies
            if sid in Global.proxy_uuids:
                logging.debug('Ignoring proxied pyre event')
                continue

            if eventtype == 'JOIN':
                channel = event[3].decode('utf-8')
                if Global.localchannelcount.get(channel,0) == 0:
                    Global.pyre.join(channel)
                    Global.localchannelcount[channel] = 0
                    server_send(['JOIN', channel])
                    logging.debug('Bridge client joining local channel %s'%(channel))
                Global.localchannelcount[channel] += 1
            elif eventtype == 'LEAVE':
                channel = event[3].decode('utf-8')
                Global.localchannelcount[channel] -= 1
                if Global.localchannelcount[channel] == 0:
                    Global.pyre.leave(channel)
                    server_send(['LEAVE', channel])
                    logging.debug('Bridge client leaving channel %s'%(channel))
            elif eventtype == 'SHOUT':
                channel = event[3].decode('utf-8')
                
                # Quit if federation QUIT message received.
                if event[4] == u'QUIT':
                    logging.warning('Bridge client received a local QUIT message. Exiting.')
                    client_quit()
                # Since the server communicates with json, we
                # need to un-json the message (which server_send
                # will re-json). There's probably a more elegant way
                # to do this.
                message = json.loads(event[4].decode('utf-8'))
                server_send(['SHOUT', name, channel, message])
# end main()

# server_send and server_recv taken almost directly from
# https://github.com/mdebbar/jsonsocket
#
# The complexity is to handle framing -- send/receive over sockets
# isn't atomic. See top of this file for comments.

def server_send(msg):
    serialized = json.dumps(msg)
    with Global.writelock:
        Global.bridgesocket.send(six.b('%d\n'%(len(serialized))))
        Global.bridgesocket.sendall(six.b(serialized))

def server_recv():
    length_str = ''
    next_offset = 0
    with Global.readlock:
        # Get the length
        char = Global.bridgesocket.recv(1)
        while char != six.b('\n'):
            length_str += char.decode('utf-8')
            char = Global.bridgesocket.recv(1)
        total = int(length_str)

        # use a memoryview to receive the data chunk by chunk efficiently
        view = memoryview(bytearray(total))
        while total - next_offset > 0:
            recv_size = Global.bridgesocket.recv_into(view[next_offset:], total - next_offset)
            next_offset += recv_size

    # Convert back to a python object
    deserialized = json.loads(view.tobytes().decode('utf-8'))
    return deserialized
# end server_recv()

def client_quit():
    '''Quit the bridge_client without throwing any errors.'''
    try:
        Global.pyre.stop()
    except:
        pass

    try:
        Global.bridgesocket.shutdown(socket.SHUT_RDWR)
    except:
        pass

    try:
        Global.bridgesocket.close()
    except:
        pass

    sys.exit(0)
# end quit_client()

def parse_arguments(strs):
    parser = argparse.ArgumentParser(description='Start a bridge client that listens for Transport traffic and forwards to a bridge server. Version %s.'%(VERSION))
    parser.add_argument('-port', type=int, default=7417, help='Bridge server port. Defaults to %(default)s.')
    parser.add_argument('-host', default='ec2-54-153-1-22.us-west-1.compute.amazonaws.com', help='Bridge server host name. Defaults to %(default)s.')
    parser.add_argument('-loglevel', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='WARNING',
                        help='Logging level (default %(default)s)')
    parser.add_argument('-version', '--version', action='version', version=str(VERSION))
    Global.args = parser.parse_args(strs)
# end parse_arguments()

def setup_logging():
    numeric_level = getattr(logging, Global.args.loglevel, None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(level=numeric_level, format="%(module)s:%(levelname)s: %(message)s")
# end setup_logging()

if __name__ == "__main__":
    main(sys.argv)

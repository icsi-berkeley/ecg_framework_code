#!/usr/bin/env python
######################################################################
#
# File: bridge_server.py
#
# Initial Version: Dec 9, 2015 Adam Janin
#
# The bridge server simply listens for messages from
# bridge clients, and then sends the received message
# to all connected clients.
#
# It knows nothing about federations, so you should
# have a separate server for each federation.
#
#
# TODO:
#
# Support python3
#

from six.moves import input

import argparse
import logging
import select
import signal
import socket
import sys

VERSION = 0.1

# Command line arguments (argparse object). Created in parse_arguments()
Args = None

# Dictionary of client socket -> address
ClientSockets = {}

# Global so server_quit() can find it.
ServerSocket = None

def main(argv):

    global ClientSockets, ServerSocket, Args

    parse_arguments(argv[1:])
    setup_logging()

    # If the user presses ctrl-C, exit cleanly.
    signal.signal(signal.SIGINT, lambda s, f: server_quit())

    # Create the server socket.
    ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ServerSocket.bind((Args.host, Args.port))
    ServerSocket.listen(5)
    (ignore, port) = ServerSocket.getsockname()
    if Args.host == '':
        host = socket.getfqdn()
    else:
        host = Args.host
    logging.warning('Server listening on %s:%d'%(host, port))

    # Listen for connections and/or messages from clients
    while True:
        sockets = list(ClientSockets.keys())
        sockets.append(ServerSocket)
        sockets.append(sys.stdin)
        # sockets now contain all the current client sockets plus
        # the server socket plus stdin.
        if Args.timeout > 0:
            si,so,se = select.select(sockets, [], [], Args.timeout)
        else:
            si,so,se = select.select(sockets, [], [])

        # If si is empty, timeout occurred.
        if len(si) == 0:
            logging.warning('Server timed out')
            server_quit()
            break

        if sys.stdin in si:
            # Got something on stdin.
            command = input()
            if command == 'quit':
                server_quit()
                break
            elif command == 'help':
                print('\nValid commands are quit and help.\n')
            else:
                logging.warning('Unknown command on stdin: "%s"'%(command))

        if ServerSocket in si:
            # New connection. Add to ClientSockets.
            (clientsocket, address) = ServerSocket.accept()
            logging.info("Got connection from %s:%d"%address)
            ClientSockets[clientsocket] = address
            continue

        # Now, for each client, check if it's sent a message
        for client in ClientSockets:
            if client in si:
                try:
                    rec = client.recv(Args.blocksize)
                except:
                    rec = None
                if rec == b'' or rec == 0 or rec == '' or rec is None:
                    # Client disconnected
                    logging.info("%s:%d disconnected"%ClientSockets[client])
                    try:
                        client.shutdown(socket.SHUT_RDWR)
                        client.close()
                    except:
                        pass  # silently ignore problems closing a cleient.
                    del ClientSockets[client]
                    # Since ClientSockets has changed, the "for client"
                    # iterator must be exited.
                    break
                logging.debug('Got data "%s"'%(rec))
                # Client sent something. Forward to all clients
                # except the client that sent it.
                for c in ClientSockets:
                    if c != client:
                        logging.debug('Sending data to %s:%d'%ClientSockets[c])
                        c.sendall(rec)
        # end for client
    # end while True
# end main()


def server_quit():
    '''Close all clients and the server'''
    global ClientSockets, ServerSocket, Args

    for c in ClientSockets:
        c.shutdown(socket.SHUT_RDWR)
        c.close()

    if ServerSocket is not None:
        ServerSocket.shutdown(socket.SHUT_RDWR)
        ServerSocket.close()
    logging.info('Server quitting')
    sys.exit(0)
# end server_quit()


def parse_arguments(strs):
    parser = argparse.ArgumentParser(description='Start a bridge server that listens for bridge client connections. When a bridge client sends a message to the server, the server echos to all other clients. Version %s.'%(VERSION))
    parser.add_argument('-port', type=int, default=7417, help='Server port to listen on. Use 0 to assign an unused non-root port. Defaults to %(default)s.')
    parser.add_argument('-host', default='', help='Which host IP to listen on. Typical settings are "localhost" if you only want connections from this host, the fully qualified host name, or blank if you want to accept connections sent to any interface the local host uses. Defaults to %(default)s.')
    parser.add_argument('-timeout', type=int, default=0, help='If the server has no activity after this amount of time, it automatically exits. Use 0 to never exit. Default is %(default)s.')
    parser.add_argument('-loglevel',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO',
                        help='Logging level (default %(default)s)')
    parser.add_argument('-version', '--version', action='version', version=str(VERSION))
    parser.add_argument('-blocksize', type=int, default=1024, help='Read at most this many bytes when a socket has data available. Only useful for debugging. Default is %(default)s.')
    global Args
    Args = parser.parse_args(strs)
# end parse_arguments()


def setup_logging():
    numeric_level = getattr(logging, Args.loglevel, None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(level=numeric_level, format="%(module)s:%(levelname)s: %(message)s")
# end setup_logging()


if __name__ == "__main__":
    main(sys.argv)

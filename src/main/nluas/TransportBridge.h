//////////////////////////////////////////////////////////////////////
//
// File: TransportBridge.h
// Author: Adam Janin
//         Feb 8, 2016
//
// See README.rst for documentation and testtb.cpp for an example.
//
//
// TODO: Error checking, exceptions (?), convenience routines (e.g. only return messages sent to myname).
//
// Currently, bridge_error() cleans up winsock and exits. Almost certainly want to do something smarter.
// Also, all errors are currently fatal. May want to add warning.
//
// Note: Other than bridge_error() calling WSACleanup, these routines don't allocate/deallocate winsock.
// You have to do it yourself once per process. E.g.:
//  WSADATA wsaData;
//  int iResult;
//  iResult = WSAStartup(MAKEWORD(2, 2), &wsaData);
//  if (iResult != 0) {
//     // report an error
//  ...
//  iResult = WSACleanup();
//  ...

#pragma once

#include <winsock2.h>

#include "rapidjson/document.h"

class TransportBridge
{
public:
	// Use port=8856 for debugging and 7417 for production.
	// The constructor handles joining myname (so that the bridge will send SHOUTs here if they're directed to myname).
	TransportBridge(const char* myname = "StarCraft", const char* bridge_host = "ec2-54-153-1-22.us-west-1.compute.amazonaws.com", int bridge_port = 8856);
	~TransportBridge();

	// Instead of throwing exception, TransportBridge methods call bridge_error()
	// Currently, it just prints a message, closes everything down, and exits.
	// Also, almost all error checking calls bridge_error, so all
	// errors are fatal. Takes printf-like arguments.
	void bridge_error(char* ...);

	// Return non-zero if data is available from the bridge (i.e. if recv will not block).
	// timeout is the number of seconds to wait until returning. Negative timeout means to wait forever.
	int data_available(long timeout = 0);

	// Read data from the bridge and store it in a json document. Note that you get back the Pyre structure, not just the tuple.
	// For example, ["SHOUT", "ProblemSolver", "StarCraft", { "Command": "Move", "Unit": ... }]
	// It's up to you to make sure the command is for you.
	// The passed document is cleared before parsing the incoming json.
        // Note that recv_json() blocks until a full message is available.
	void recv_json(rapidjson::Document*);

	// Send a JSON document. You must include the pyre pieces yourself (e.g. ["SHOUT", "StarCraft", "ProblemSover", { "UnitAppeared": "Firebat", "Location": [ ... ] } ]
	void send_json(rapidjson::Document*);
	
	// Send a STRING to the bridge. Useful if you want to format the JSON yourself. You must
	// include the pyre pieces yourself (e.g. "[\"JOIN\", \"GLOBAL\"]").
	void send_string(const char*);

	// Public in case you want to fiddle directly.
	SOCKET bridge_socket;
	int bridge_port;
	char* bridge_host;
	char* myname;
};

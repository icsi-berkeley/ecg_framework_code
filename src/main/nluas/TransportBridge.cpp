//////////////////////////////////////////////////////////////////////
//
// File: TransportBridge.cpp
// Author: Adam Janin
//         Feb 8, 2016
//
// See README.rst and TransportBridge.h for documentation and
// testtb.cpp for an example.

#include "stdafx.h"
#include "TransportBridge.h"

#include <winsock2.h>
#include <ws2tcpip.h>
#include <stdio.h>

#include "rapidjson/document.h"
#include "rapidjson/stringbuffer.h"
#include "rapidjson/writer.h"

TransportBridge::TransportBridge(const char* amyname, const char* abridge_host, int abridge_port)
{
	bridge_host = _strdup(abridge_host);
	bridge_port = abridge_port;
	myname = _strdup(amyname);

	struct addrinfo *result = NULL,
		*ptr = NULL,
		hints;
	int iResult;

	// convert the port # to a string.
	char bridge_port_str[1024];
	_snprintf_s(bridge_port_str, 1024, _TRUNCATE, "%d", bridge_port);

	// Resolve the server address and port

	ZeroMemory(&hints, sizeof(hints));
	hints.ai_family = AF_UNSPEC;
	hints.ai_socktype = SOCK_STREAM;
	hints.ai_protocol = IPPROTO_TCP;

	iResult = getaddrinfo(bridge_host, bridge_port_str, &hints, &result);
	if (iResult != 0) {
		bridge_error("getaddrinfo failed with error: %d\n", iResult);
	}

	// Attempt to connect to an address until one succeeds
	for (ptr = result; ptr != NULL; ptr = ptr->ai_next) {
		// Create a SOCKET for connecting to server
		bridge_socket = socket(ptr->ai_family, ptr->ai_socktype, ptr->ai_protocol);
		if (bridge_socket == INVALID_SOCKET) {
			bridge_error("socket failed with error: %ld\n", WSAGetLastError());
		}
		// Connect to server.
		iResult = connect(bridge_socket, ptr->ai_addr, (int)ptr->ai_addrlen);
		if (iResult == SOCKET_ERROR) {
			closesocket(bridge_socket);
			bridge_socket = INVALID_SOCKET;
			continue;
		}
		break;
	}

	freeaddrinfo(result);

	if (bridge_socket == INVALID_SOCKET) {
		bridge_error("Unable to connect to server!\n");
	}

#define BRIDGE_JOIN_BUFSIZE (1024)
	char buf[BRIDGE_JOIN_BUFSIZE];
	_snprintf_s(buf, BRIDGE_JOIN_BUFSIZE, _TRUNCATE, "[\"JOIN\", \"%s\"]", myname);
	send_string(buf);

} // TransportBridge()


TransportBridge::~TransportBridge()
{
	int iResult;

	iResult = shutdown(bridge_socket, SD_SEND);
	if (iResult == SOCKET_ERROR) {
		int err = WSAGetLastError();
		closesocket(bridge_socket);
		bridge_error("shutdown failed with error: %d\n", err);
	}

	free(bridge_host);
	free(myname);
} // ~TransportBridge()

void TransportBridge::bridge_error(char* fmt ...) {
	va_list args;
	va_start(args, fmt);
	fprintf(stderr, "transport bridge error: ");
	vfprintf(stderr, fmt, args);
	va_end(args);
	fprintf(stderr, ".\n");
	WSACleanup();  // clean up winsock
	exit(1);       // exit
} // TransportBridge::bridge_error()

int TransportBridge::data_available(long timeout) {
	fd_set readset;
	int nset;
	TIMEVAL tv;

	FD_ZERO(&readset);
	FD_SET(bridge_socket, &readset);
	if (timeout >= 0) {
	        tv.tv_sec = timeout;
		tv.tv_usec = 0L;
		nset = select(1, &readset, NULL, NULL, &tv);
	}
	else {
		nset = select(1, &readset, NULL, NULL, NULL);
	}
	if (nset == 0) {
		return 0;
	}
	else if (FD_ISSET(bridge_socket, &readset)) {
		return 1;
	}
	else {
		bridge_error("Unexpected return from select %d", nset);
	}
	return 0; // Should never get here, but needed to shut up warning.
} // TransportBridge::data_available()


// Send a string to the bridge. You must handle the pyre stuff yourself, but send_string()
// handles encoding for the bridge (i.e. the length of the string).

#define BRIDGE_SEND_BUFSIZE (1024)
void TransportBridge::send_string(const char* sendbuf) {
	int iResult;
	// First send the length.
	char buf[BRIDGE_SEND_BUFSIZE];
	_snprintf_s(buf, BRIDGE_SEND_BUFSIZE, _TRUNCATE, "%d\n", strlen(sendbuf)); // Probably need to check errors here...
	iResult = send(bridge_socket, buf, (int)strlen(buf), 0);
	if (iResult == SOCKET_ERROR) {
		int err = WSAGetLastError();
		closesocket(bridge_socket);
		bridge_error("send length failed with error: %d\n", err);
	}

	iResult = send(bridge_socket, sendbuf, (int)strlen(sendbuf), 0);
	if (iResult == SOCKET_ERROR) {
		int err = WSAGetLastError();
		closesocket(bridge_socket);
		bridge_error("send failed with error: %d\n", err);
	}
} // TransportBridge::send_string()

// Receive data from the Bridge. It is encoded as an ascii length
// followed by newline followed by that number of bytes in a JSON
// string. This is complex because socket communication is not
// guaranteed to be atomic (i.e. one write may become many reads).

#define BRIDGE_RECV_BUFSIZE (10000)
void TransportBridge::recv_json(rapidjson::Document* document) {
	char recvbuf[BRIDGE_RECV_BUFSIZE];
	int iResult;
	int pos = 0;
	int len;

	// First info should be the number of bytes in the string followed by newline.
	while (1) {
		iResult = recv(bridge_socket, recvbuf + pos, 1, 0);
		if (iResult == 0) {
			// Connection closed.
			bridge_error("Remote bridge closed trying to read length.\n");
		}
		else if (iResult != 1) {
			// Some other error
			bridge_error("recv failed reading length with error: %d\n", WSAGetLastError());
		}
		// Read one byte. If it's newline, we should have now received a full length string.
		if (recvbuf[pos] == '\n') {
			break;
		}
		// Error if it isn't a digit.
		if (!isdigit(recvbuf[pos])) {
			bridge_error("recv got a non-digit in the length field.\n");
		}
		if (pos >= BRIDGE_RECV_BUFSIZE-1) {
			bridge_error("recv got a very long length field.\n");
		}
		pos++;
	}
	// If we get here, we should have a legal length in recvbuf.
	len = -1;
	if (sscanf_s(recvbuf, "%d", &len) != 1 || len < 1) {
		bridge_error("Got illegal length string \"%s\"\n", recvbuf);
	}
	if (len >= BRIDGE_RECV_BUFSIZE-1) {
		bridge_error("length too long (max %d, got %d)\n", BRIDGE_RECV_BUFSIZE, len);
	}
	// Now read until we get len bytes.
	int nread = 0;
	while (nread < len) {
		iResult = recv(bridge_socket, recvbuf + nread, len - nread, 0);
		if (iResult == 0) {
			bridge_error("Remote bridge closed.\n");
		}
		else if (iResult < 0) {
			bridge_error("recv failed with error: %d\n", WSAGetLastError());
		}
		nread += iResult;
	}
	recvbuf[nread] = 0; // null terminate.
	document->SetArray(); // This should clear any existing allocation. Not sure if needed.
	document->Parse(recvbuf); // Parse the json into the document.
}  // TransportBridge::recv_json()

void TransportBridge::send_json(rapidjson::Document* doc) {
	rapidjson::StringBuffer buffer;
	rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
	doc->Accept(writer);
	const char* output = buffer.GetString();
	send_string(output);
} // TransportBridge::send_json()




//////////////////////////////////////////////////////////////////////
//
// Example of using TransportBridge. Just wait for a message from
// chat1 and then reply. See README.rst and TransportBridge.h for
// information.
//

#include "stdafx.h"
#include <winsock2.h>
#include <ws2tcpip.h>
#include <stdio.h>

#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include "TransportBridge.h"

#pragma comment(lib, "Ws2_32.lib")

// Just a sample main
int __cdecl main(int argc, char**argv) {
  if (argc != 1) {
    fprintf(stderr, "usage: %s\n", argv[0]);
    exit(1);
  }

  // Initialize Winsock

  WSADATA wsaData;
  int iResult;

  iResult = WSAStartup(MAKEWORD(2, 2), &wsaData);
  if (iResult != 0) {
    fprintf(stderr, "WSAStartup failed with error: %d\n", iResult);
    exit(1);
  }

  // Create the transport bridge with default settings for
  // name and Bridge Server location.
	
  TransportBridge tb;

  // Place to store data from server.
  rapidjson::Document doc;

  while (1) {
    printf("waiting for data from socket.\n");
    if (tb.data_available(30)) {	// Wait up to 30 seconds.
      printf("data available on socket.\n");
      tb.recv_json(&doc);
	  // Check if it's for me
      if (!strcmp(doc[0].GetString(), "SHOUT") &&
		  !strcmp(doc[2].GetString(), "StarCraft")) {
		// Print message
		rapidjson::StringBuffer strbuf;
		rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
		doc[3].Accept(writer);
		printf("Got message from %s: %s\n", doc[1].GetString(), strbuf.GetString());

		// Send a reply to whoever sent the message.
		char charbuf[1024];
		_snprintf_s(charbuf, 1024, _TRUNCATE, "[\"SHOUT\", \"StarCraft\", \"%s\", \"Ack ack\"]", doc[1].GetString());
		tb.send_string(charbuf);
      }
    } else {
      printf("timed out.\n");
    }
  }

  // Shut down winsock.
  iResult = WSACleanup();
  if (iResult != 0) {
    fprintf(stderr, "WSACleanup failed with error: %d\n", iResult);
    exit(1);
  }

  return 0;
} // main()

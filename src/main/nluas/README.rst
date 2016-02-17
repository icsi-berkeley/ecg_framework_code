This is all very preliminary. I expect we'll change things as we gain
experience. Specifically, we'll probably want to add some convenience
routines for stuff we do regularly.

The source of this file is in rst (reStructuredText) format, which is
mostly plain text, but allows easy conversion to pdf and html.


Overview
========

TransportBridge is a C++ class that communicates directly with the
Bridge Server in order to allow you to communicate with python
Transports. It uses the library rapidjson (http://rapidjson.org) for
JSON encoding and decoding. Note that TransportBridge uses a lower
level protocol (known as Pyre) than Transport, so it's a bit more
complicated to use.

Example Usage::

 // Create a TransportBridge object with default info
 TransportBridge tb;

 // Create a rapidjson document for storing the results.
 rapidjson::Document doc;

 // Block until there's a message from the BridgeServer.
 // Store it in doc.
 tb.recv_json(&doc);

 // doc now contains a Pyre message from the BridgeServer.

The only Pyre message you probably care about is SHOUT::

 ["SHOUT", "chat1", "StarCraft", "message from chat1"]

This message means that chat1 sent a message to StarCraft, and the
message was the simple string "message from chat1" (the message could
itself be a json object).

Since you probably don't care about other messages, you should do
something like::

 if (!strcmp(doc[0].GetString(), "SHOUT") &&
     !strcmp(doc[2].GetString(), "StarCraft")) {
     	 ... handle message ...


TransportBridge::data_available()
=================================

Another function you'll use is ``tb.data_available()``. It checks if
there's any data from the Bridge Server waiting to be processed. By
default, ``tb.data_available()`` returns immediately. This is useful
if you're calling it in a periodic event loop (e.g. per frame in
StarCraft). You can also pass it an integer timeout, which is the
number of seconds to block waiting to see if data is available.


TransportBridge::send_*
=======================

You can send a message to any Transport by using ``tb.send_string()``
or ``tb.send_json()``. Note that you must format the message as a JSON
encoded Pyre message. For example::

 tb.send_string("[\"SHOUT\", \"StarCraft\", \"chat1\", \"a message\"]")

This will send the simple string "a message" FROM StarCraft TO chat1.
As long as chat1 has subscribed to StarCraft messages (and the bridge
is set up correctly), the message will be delivered.

``tb.send_json()`` is similar, but you can pass it a rapidjson
document instead of a string.

(We'll probably want to add some convenience routines,
e.g. printf-like or cout-like variants).

Installing
==========

Just add TransportBridge.cpp and TransportBridge.h to your project.
The assumption is that they're in the same directory. You also need
the header files from rapidjson (http://rapidjson.org). They're
assumed to be in a directory names rapidjson in the same place as
TransportBridge.cpp and TransportBridge.h. Edit the ``#include
"rapidjson`` lines in the C++ files if you change the location.

NOTES
=====

1. You must initialize/finalize winsock yourself. See testmain.cpp or
TransportBridge.h for examples.

2. You should not allow too many messages to queue up. In other words, be
sure to call ``tb.recv_json`` every once in a while. Otherwise, you can fill
up OS queues and cause everything to grind to a halt.

3. The remote Bridge Server and Bridge Clients must already be running
when you create a TransportBridge.

4. The tb.recv_json() call block until a full message is
available. Either call tb.recv_json() from an independent thread, or
combine with e.g.::

 if (tb.data_available()) {
   tb.recv_json(doc);
   ...

5. See TransportBridge.h for more code-level documentation and
testtb.cpp for a complete console example.

6. I strongly suspect Unicode will cause everything to die a horrible
death. Try to stick with ascii.

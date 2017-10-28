#!/usr/bin/env python

"""
The MIT License (MIT)
Copyright (c) 2015 Maker Musings
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

# For a complete discussion, see http://www.makermusings.com
import os
import gc
import urequests
import uselect
import usocket
import struct
import sys
import time
import timeutils
import urllib
import machine
import network

import _thread

# for ws2812b
from ws2812 import WS2812


# This XML is the minimum needed to define one of our virtual switches
# to the Amazon Echo

SETUP_XML = """<?xml version="1.0"?>
<root>
  <device>
    <deviceType>urn:LeMaRiva:device:controllee:1</deviceType>
    <friendlyName>%(device_name)s</friendlyName>
    <manufacturer>Belkin International Inc.</manufacturer>
    <modelName>Emulated Socket</modelName>
    <modelNumber>3.1415</modelNumber>
    <UDN>uuid:Socket-1_0-%(device_serial)s</UDN>
  </device>
</root>
"""


DEBUG = False
INADDR_ANY = 0
global_epoch = 0        # time over ntp-server

# W2812b
ledNumber = 144         # number of leds
chain = []

def dbg(msg):
    global DEBUG
    if DEBUG:
        print (msg)

def inet_aton(addr):
    ip_as_bytes = bytes(map(int, addr.split('.')))
    return ip_as_bytes

# A simple utility class to wait for incoming data to be
# read on a socket.
class poller:
    def __init__(self):
        if 'poll' in dir(uselect):
            self.use_poll = True
            self.poller = uselect.poll()
        else:
            self.use_poll = False
        self.targets = {}
        global_epoch = timeutils.epoch()

    def add(self, target, socket = None):
        if not socket:
            socket = target.sockets()
        if self.use_poll:
            self.poller.register(socket, uselect.POLLIN)
        #dbg("add device on fileno: %s" % socket.fileno() )
        self.targets[socket.fileno()] = target
        #dbg("size targets: %s" % len(self.targets))


    def remove(self, target, socket = None):
        if not socket:
            socket = target.sockets()
        if self.use_poll:
            self.poller.unregister(socket)
        #dbg("remove device on fileno: %s" % socket.fileno() )
        del(self.targets[socket.fileno()])

    def poll(self, timeout = 100):
        if self.use_poll:
            ready = self.poller.poll(timeout)
        else:
            ready = []
            if len(self.targets) > 0:
                (rlist, wlist, xlist) = uselect.select(self.targets.keys(), [], [], timeout)
                ready = [(x, None) for x in rlist]

        for one_ready in ready:
            target = self.targets.get(one_ready[0].fileno(), None)
            dbg("Targets %s" % str(self.targets.keys()))
            if target:
                #dbg("get socket with fileno: %s" % str(one_ready[0].fileno()) +  " len: %s" % len(one_ready) + " selected: %s " % str(target.fileno()) )
                # update time
                target.do_read(one_ready[0])

# Base class for a generic UPnP device. This is far from complete
# but it supports either specified or automatic IP address and port
# selection.

class upnp_device:
    this_host_ip = None

    @staticmethod
    def local_ip_address():
        if not upnp_device.this_host_ip:
            try:
                ap_if = network.WLAN()
                upnp_device.this_host_ip = ap_if.ifconfig()[0]
            except:
                upnp_device.this_host_ip = '127.0.0.1'
            dbg("got local address of %s" % upnp_device.this_host_ip)
        return upnp_device.this_host_ip


    def __init__(self, listener, poller, port, root_url, server_version, persistent_uuid, other_headers = None, ip_address = None):
            self.listener = listener
            self.poller = poller
            self.port = port
            self.root_url = root_url
            self.server_version = server_version
            self.persistent_uuid = persistent_uuid
            self.uuid = machine.unique_id()#uuid.uuid4()
            self.other_headers = other_headers

            if ip_address:
                self.ip_address = ip_address
            else:
                self.ip_address = upnp_device.local_ip_address()

            self.socket = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
            self.socket.bind((self.ip_address, self.port))
            self.socket.listen(5)
            if self.port == 0:
                self.port = self.socket.getsockname()[1]
            self.poller.add(self)
            self.client_sockets = {}
            self.listener.add_device(self)

    def fileno(self):
        return self.socket.fileno()

    def sockets(self):
        return self.socket

    def do_read(self, socket):

        fileno = socket.fileno()
        dbg("Fileno %s" % fileno + " socket fileno %s" % self.socket.fileno())

        if fileno == self.socket.fileno():
            try:
                (client_socket, client_address) = self.socket.accept()
                self.poller.add(self, client_socket)
                self.client_sockets[client_socket.fileno()] = client_socket
            except Exception as e:
                dbg("Socket busy! %s" % str(e))
        else:
            data, sender = self.client_sockets[fileno].recvfrom(4096)
            if not data:
                self.poller.remove(self, self.client_sockets[fileno])
                self.client_sockets[fileno].close()
                del(self.client_sockets[fileno])
            else:
                dbg("send response to socket!: %s" % str(fileno))
                self.handle_request(data, sender, self.client_sockets[fileno])


    def handle_request(self, data, sender, socket):
        pass

    def get_name(self):
        return "unknown"

    def respond_to_search(self, destination, search_target):
        dbg("Responding to search for %s" % self.get_name())
        date_str = timeutils.formatdate(global_epoch)
        location_url = self.root_url % {'ip_address' : self.ip_address, 'port' : self.port}
        message = ("HTTP/1.1 200 OK\r\n"
                  "CACHE-CONTROL: max-age=86400\r\n"
                  "DATE: %s\r\n"
                  "EXT:\r\n"
                  "LOCATION: %s\r\n"
                  "OPT: \"http://schemas.upnp.org/upnp/1/0/\"; ns=01\r\n"
                  "01-NLS: %s\r\n"
                  "SERVER: %s\r\n"
                  "ST: %s\r\n"
                  "USN: uuid:%s::%s\r\n" % (date_str, location_url, self.uuid, self.server_version, search_target, self.persistent_uuid, search_target))
        if self.other_headers:
            for header in self.other_headers:
                message += "%s\r\n" % header
        message += "\r\n"

        try:
            temp_socket = usocket.socket(usocket.AF_INET,usocket.SOCK_DGRAM)
            #print("temp_socket %s" % temp_socket.fileno())
            #print("destination" + str(destination) + "message" + message)
            temp_socket.sendto(message, destination)
            temp_socket.close()
            del(temp_socket)
        except Exception as e:
            dbg("Got problem to send response %s" % str(e))
        temp_socket = None
# This subclass does the bulk of the work to mimic a WeMo switch on the network.

class fauxmo(upnp_device):
    @staticmethod
    def make_uuid(name):
        return ''.join(["%x" % sum([ord(c) for c in name])] + ["%x" % ord(c) for c in "%sfauxmo!" % name])[:14]

    def __init__(self, name, listener, poller, ip_address, port, action_handler = None):
        self.serial = self.make_uuid(name)
        self.name = name
        self.ip_address = ip_address
        persistent_uuid = "Socket-1_0-" + self.serial
        other_headers = ['X-User-Agent: redsonic']
        upnp_device.__init__(self, listener, poller, port, "http://%(ip_address)s:%(port)s/setup.xml", "Unspecified, UPnP/1.0, Unspecified", persistent_uuid, other_headers=other_headers, ip_address=ip_address)
        if action_handler:
            self.action_handler = action_handler
        else:
            self.action_handler = self
        dbg("FauxMo device '%s' ready on %s:%s" % (self.name, self.ip_address, self.port))

    def get_name(self):
        return self.name

    def handle_request(self, data, sender, socket):
        if data.find(b'GET /setup.xml HTTP/1.1') == 0:
            dbg("Responding to setup.xml for %s" % self.name)
            xml = SETUP_XML % {'device_name' : self.name, 'device_serial' : self.serial}
            date_str = timeutils.formatdate(global_epoch)
            message = ("HTTP/1.1 200 OK\r\n"
                       "CONTENT-LENGTH: %d\r\n"
                       "CONTENT-TYPE: text/xml\r\n"
                       "DATE: %s\r\n"
                       "LAST-MODIFIED: Sat, 01 Jan 2000 00:01:15 GMT\r\n"
                       "SERVER: Unspecified, UPnP/1.0, Unspecified\r\n"
                       "X-User-Agent: redsonic\r\n"
                       "CONNECTION: close\r\n"
                       "\r\n"
                       "%s" % (len(xml), date_str, xml))
            socket.send(message)
        elif data.find(b'SOAPACTION: "urn:Belkin:service:basicevent:1#SetBinaryState"') != -1:
            success = False
            if data.find(b'<BinaryState>1</BinaryState>') != -1:
                # on
                dbg("Responding to ON for %s" % self.name)
                success = self.action_handler.on()
            elif data.find(b'<BinaryState>0</BinaryState>') != -1:
                # off
                dbg("Responding to OFF for %s" % self.name)
                success = self.action_handler.off()
            else:
                dbg("Unknown Binary State request:")

            if success:
                # The echo is happy with the 200 status code and doesn't
                # appear to care about the SOAP response body
                soap = ""
                date_str = timeutils.formatdate(global_epoch)
                message = ("HTTP/1.1 200 OK\r\n"
                           "CONTENT-LENGTH: %d\r\n"
                           "CONTENT-TYPE: text/xml charset=\"utf-8\"\r\n"
                           "DATE: %s\r\n"
                           "EXT:\r\n"
                           "SERVER: Unspecified, UPnP/1.0, Unspecified\r\n"
                           "X-User-Agent: redsonic\r\n"
                           "CONNECTION: close\r\n"
                           "\r\n"
                           "%s" % (len(soap), date_str, soap))
                socket.send(message)
        else:
            dbg(data)

    def on(self):
        return False

    def off(self):
        return True


# Since we have a single process managing several virtual UPnP devices,
# we only need a single listener for UPnP broadcasts. When a matching
# search is received, it causes each device instance to respond.
#
# Note that this is currently hard-coded to recognize only the search
# from the Amazon Echo for WeMo devices. In particular, it does not
# support the more common root device general search. The Echo
# doesn't search for root devices.

class upnp_broadcast_responder:
    TIMEOUT = 0

    def __init__(self):
        self.devices = []

    def init_socket(self):
        ok = True
        self.ip = '239.255.255.250'
        self.port = 1900
        try:
            #This is needed to join a multicast group
            self.mreq = struct.pack("4sl",inet_aton(self.ip), INADDR_ANY)
            #Set up server socket
            self.ssock = usocket.socket(usocket.AF_INET,usocket.SOCK_DGRAM)
            self.ssock.setsockopt(usocket.SOL_SOCKET,usocket.SO_REUSEADDR,1)
            try:
                self.ssock.bind(('',self.port))
            except Exception as e:
                dbg("WARNING: Failed to bind %s:%d: %s" , (self.ip,self.port,e))
                ok = False
            try:
                #dbg("IP: " + str(usocket.IPPROTO_IP) + " IP_ADD_MEMBERSHIP: " + str(usocket.IP_ADD_MEMBERSHIP) + " mreq: " + str(self.mreq) )
                self.ssock.setsockopt(usocket.IPPROTO_IP,usocket.IP_ADD_MEMBERSHIP,self.mreq)
            except Exception as e:
                dbg('WARNING: Failed to join multicast group!: ' + str(e))
                ok = False

        except Exception as e:
            dbg("Failed to initialize UPnP sockets!")
            return False
        if ok:
            dbg("Listening for UPnP broadcasts")

    def fileno(self):
        return self.ssock.fileno()

    def sockets(self):
        return self.ssock

    def do_read(self, fileno):
        data, sender = self.recvfrom(1024)
        if data:
            if data.find(b'M-SEARCH') == 0 and data.find(b'urn:Belkin:device:**') != -1:
                for device in self.devices:
                    device.respond_to_search(sender, 'urn:Belkin:device:**')
            else:
                pass

    #Receive network data
    def recvfrom(self,size):
        if self.TIMEOUT:
            self.ssock.setblocking(0)
            ready = uselect.select([self.ssock], [], [], self.TIMEOUT)[0]
        else:
            self.ssock.setblocking(1)
            ready = True

        try:
            if ready:
                return self.ssock.recvfrom(size)
            else:
                return False, False
        except Exception as e:
            dbg(e)
            return False, False

    def add_device(self, device):
        self.devices.append(device)
        dbg("UPnP broadcast listener: new device registered")


# This is an example handler class. The fauxmo class expects handlers to be
# instances of objects that have on() and off() methods that return True
# on success and False otherwise.
#
# This example class takes a color and brightness. It ignores any return data.

class rest_api_handler(object):
    def __init__(self, on_color, on_brightness):
        global ledNumber
        global ws2812_chain
        self.on_color = on_color
        self.on_brightnessr = on_brightness

        ws2812_chain.set_brightness(on_brightness)

    def on(self):
        global ledNumber
        global ws2812_chain

        #global_epoch = timeutils.epoch() # updating time using ntp

        data = [self.on_color for i in range(ledNumber)]

        ws2812_chain.show( data )

        dbg("response on")
        return True

    def off(self):
        global ledNumber
        global ws2812_chain

        #global_epoch = timeutils.epoch() # updating time using ntp

        data = [(0,0,0) for i in range(ledNumber)]

        ws2812_chain.show( data )

        dbg("response off")
        return True


# Each entry is a list with the following elements:
#
# name of the virtual switch
# object with 'on' and 'off' methods
# port # (optional; may be omitted)


# Exception definitions that are used in the package
class InvalidPortException(Exception):
    pass


def thread_echo(args):
    global DEBUG
    global ws2812_chain
    # Set up our singleton for polling the sockets for data ready

    ws2812_chain =  WS2812(ledNumber=ledNumber, brightness=100)
    p = poller()

    # NOTE: As of 2015-08-17, the Echo appears to have a hard-coded limit of
    # 16 switches it can control. Only the first 16 elements of the 'devices'
    # list will be used.
    devices = [
        {"description": "white lights",
         "port": 12340,
         "handler": rest_api_handler((255,255,255), 50)},
        {"description": "red lights",
         "port": 12341,
         "handler": rest_api_handler((255,0,0), 50)},
        {"description": "blue lights",
         "port": 12342,
         "handler": rest_api_handler((30,144,255), 90)},
        {"description": "green lights",
          "port": 12343,
          "handler": rest_api_handler((0,255,0), 90)},
	    {"description": "orange lights",
		  "port": 12345,
		  "handler": rest_api_handler((255,165,0), 90)},
    ]

    # Set up our singleton listener for UPnP broadcasts
    u = upnp_broadcast_responder()
    u.init_socket()

    # Add the UPnP broadcast listener to the poller so we can respond
    # when a broadcast is received.
    p.add(u)

    # Create our FauxMo virtual switch devices
    # Initialize FauxMo devices
    for device in devices:
        #if `port` doesnt exist, populate it
        #if it isnt an int, flip out with a descriptive exception
        if not device.get("port"):
            device["port"] = 0
        elif type(device["port"]) is not int:
            raise InvalidPortException("Invalid port of type: {}, with a value of: {}".format(type(device["port"]), device["port"]))
        fauxmo(device["description"], u, p, None, device["port"], action_handler = device["handler"])

    dbg("Entering main loop\n")
    while True:
        try:
            # Allow time for a ctrl-c to stop the process
            p.poll(10)
            time.sleep(0.1)
            gc.collect()
        except Exception as e:
            dbg(e)
            break


dbg("Starting echo service on separated thread\n")
_thread.start_new_thread(thread_echo, ('',))

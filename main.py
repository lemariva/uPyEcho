#!/usr/bin/env python

"""
The MIT License (MIT)
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

Copyright (c) 2015 Maker Musings
Copyright (c) 2018 Mauro Riva (lemariva.com) for MicroPython on ESP32 and Amazon Echo 2nd Gen.

For a complete discussion, see http://www.makermusings.com
More info about the MicroPython Version see https://lemariva.com

"""
import gc
import machine
import network
import time

try:
    import _thread
    thread_available = True
except:
    thread_available = False

try:
    import uselect as select
except:
    import socket
try:
    import usocket as socket
except:
    import socket
try:
    import ustruct as struct
except:
    import struct

# for ws2812b
from ws2812 import WS2812
from uos import uname

try:
    from machine import RTC
except:
    from timeutils import RTC

# This XML is the minimum needed to define one of our virtual switches
# to the Amazon Echo Dot / Amazon Echo (2nd generation)

SETUP_XML = """<?xml version="1.0"?>
<root>
  <device>
    <deviceType>urn:LeMaRiva:device:controllee:1</deviceType>
    <friendlyName>%(device_name)s</friendlyName>
    <manufacturer>Belkin International Inc.</manufacturer>
    <modelName>Emulated Socket</modelName>
    <modelNumber>3.1415</modelNumber>
    <UDN>uuid:Socket-1_0-%(device_serial)s</UDN>
    <serialNumber>221517K0101769</serialNumber>
    <binaryState>0</binaryState>
    <serviceList>
      <service>
          <serviceType>urn:Belkin:service:basicevent:1</serviceType>
          <serviceId>urn:Belkin:serviceId:basicevent1</serviceId>
          <controlURL>/upnp/control/basicevent1</controlURL>
          <eventSubURL>/upnp/event/basicevent1</eventSubURL>
          <SCPDURL>/eventservice.xml</SCPDURL>
      </service>
    </serviceList>
  </device>
</root>
"""

eventservice_xml = """<?scpd xmlns="urn:Belkin:service-1-0"?>
<actionList>
  <action>
    <name>SetBinaryState</name>
    <argumentList>
      <argument>
        <retval/>
        <name>BinaryState</name>
        <relatedStateVariable>BinaryState</relatedStateVariable>
        <direction>in</direction>
      </argument>
    </argumentList>
     <serviceStateTable>
      <stateVariable sendEvents="yes">
        <name>BinaryState</name>
        <dataType>Boolean</dataType>
        <defaultValue>0</defaultValue>
      </stateVariable>
      <stateVariable sendEvents="yes">
        <name>level</name>
        <dataType>string</dataType>
        <defaultValue>0</defaultValue>
      </stateVariable>
    </serviceStateTable>
  </action>
</scpd>
"""

GetBinaryState_soap = """<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:GetBinaryStateResponse xmlns:u="urn:Belkin:service:basicevent:1">
      <BinaryState>%(state_realy)s</BinaryState>
    </u:GetBinaryStateResponse>
  </s:Body>
</s:Envelope>
"""

DEBUG = True

INADDR_ANY = 0
global_epoch = 0        # time over ntp-server

# W2812b
ledNumber = 144         # number of leds
chain = []
clock = None


def dbg(msg):
    global DEBUG
    if DEBUG:
        print (msg)


def inet_aton(addr):
    ip_as_bytes = bytes(map(int, addr.split('.')))
    return ip_as_bytes


def format_timetuple_and_zone(timetuple, zone):
    return '%s, %02d %s %04d %02d:%02d:%02d %s' % (
        ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][timetuple[6]],
        timetuple[2],
        ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][timetuple[1] - 1],
        timetuple[0], timetuple[3], timetuple[4], timetuple[5],
        zone)


class poller:
    # A simple utility class to wait for incoming data to be
    # read on a socket.
    def __init__(self):
        if 'poll' in dir(select):
            self.use_poll = True
            self.poller = select.poll()
        else:
            self.use_poll = False
        self.targets = {}

    def add(self, target, socket=None):
        if not socket:
            socket = target.sockets()
        if self.use_poll:
            self.poller.register(socket, select.POLLIN)
        #dbg("add device on fileno: %s" % socket.fileno() )
        self.targets[socket.fileno()] = target
        #dbg("size targets: %s" % len(self.targets))

    def remove(self, target, socket=None):
        if not socket:
            socket = target.sockets()
        if self.use_poll:
            self.poller.unregister(socket)
        #dbg("remove device on fileno: %s" % socket.fileno() )
        gc.collect()

    def poll(self, timeout=100):
        if self.use_poll:
            ready = self.poller.poll(timeout)
        else:
            ready = []
            if len(self.targets) > 0:
                (rlist, wlist, xlist) = select.select(self.targets.keys(), [], [], timeout)
                ready = [(x, None) for x in rlist]

        for one_ready in ready:
            target = self.targets.get(one_ready[0].fileno(), None)
            dbg("Targets %s" % str(self.targets.keys()))
            if target:
                #dbg("get socket with fileno: %s" % str(one_ready[0].fileno()) +  " len: %s" % len(one_ready) + " selected: %s " % str(target.fileno()) )
                # update time
                target.do_read(one_ready[0])


class upnp_device:
    """
     Base class for a generic UPnP device. This is far from complete
     but it supports either specified or automatic IP address and port
     selection.
    """
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

    def __init__(self, listener, poller, port, root_url, server_version, persistent_uuid, other_headers=None, ip_address=None):
            self.listener = listener
            self.poller = poller
            self.port = port
            self.root_url = root_url
            self.server_version = server_version
            self.persistent_uuid = persistent_uuid
            self.uuid = machine.unique_id()
            self.other_headers = other_headers

            if ip_address:
                self.ip_address = ip_address
            else:
                self.ip_address = upnp_device.local_ip_address()

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
                dbg("################################## Socket busy! %s" % str(e))
        else:
            data, sender = self.client_sockets[fileno].recvfrom(4096)
            if not data:
                self.poller.remove(self, self.client_sockets[fileno])
                self.client_sockets[fileno].close()

            else:
                dbg("send response to socket!: %s" % str(fileno))
                self.handle_request(data, sender, self.client_sockets[fileno])
            gc.collect()

    def handle_request(self, data, sender, socket):
        pass

    def get_name(self):
        return "unknown"

    def respond_to_search(self, destination, search_target):
        dbg("Responding to search for %s" % self.get_name())
        date_str = format_timetuple_and_zone(clock.gmtime(), 'GMT')
        location_url = self.root_url % {'ip_address': self.ip_address, 'port': self.port}
        message = ("HTTP/1.1 200 OK\r\n"
                   "CACHE-CONTROL: max-age=86400\r\n"
                   "DATE: %s\r\n"
                   "EXT:\r\n"
                   "LOCATION: %s\r\n"
                   "OPT: \"http://schemas.upnp.org/upnp/1/0/\"; ns=01\r\n"
                   "01-NLS: %s\r\n"
                   "SERVER: %s\r\n"
                   "ST: %s\r\n"
                   "USN: uuid:%s::%s\r\n"
                   "X-User-Agent: redsonic\r\n\r\n" % (date_str, location_url, self.uuid, self.server_version, search_target, self.persistent_uuid, search_target))

        if self.other_headers:
            for header in self.other_headers:
                message += "%s\r\n" % header
        message += "\r\n"

        try:
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_socket.sendto(message, destination)
            temp_socket.close()
            gc.collect()
        except Exception as e:
            dbg("Got problem to send response %s" % str(e))


class fauxmo(upnp_device):
    """
     This subclass does the bulk of the work to mimic a WeMo switch on the network.
    """

    @staticmethod
    def make_uuid(name):
        return ''.join(["%x" % sum([ord(c) for c in name])] + ["%x" % ord(c) for c in "%sfauxmo!" % name])[:14]

    def __init__(self, name, listener, poller, ip_address, port, action_handler=None):
        self.serial = self.make_uuid(name)
        self.name = name
        self.ip_address = ip_address
        self.relayState = 0
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
        if data.find(b'POST /upnp/control/basicevent1 HTTP/1.1') == 0 and data.find(b'urn:Belkin:service:basicevent:1#GetBinaryState') != -1:
            state = self.getState()
            soap = GetBinaryState_soap % {'state_realy': state}
            date_str = format_timetuple_and_zone(clock.gmtime(), 'GMT')
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
        elif data.find(b'GET /eventservice.xml HTTP/1.1') == 0:
            dbg("Responding to eventservice.xml for %s" % self.name)
            date_str = format_timetuple_and_zone(clock.gmtime(), 'GMT')
            message = ("HTTP/1.1 200 OK\r\n"
                       "CONTENT-LENGTH: %d\r\n"
                       "CONTENT-TYPE: text/xml\r\n"
                       "DATE: %s\r\n"
                       "LAST-MODIFIED: Sat, 01 Jan 2000 00:01:15 GMT\r\n"
                       "SERVER: Unspecified, UPnP/1.0, Unspecified\r\n"
                       "X-User-Agent: redsonic\r\n"
                       "CONNECTION: close\r\n"
                       "\r\n"
                       "%s" % (len(eventservice_xml), date_str, eventservice_xml))
            socket.send(message)
        elif data.find(b'GET /setup.xml HTTP/1.1') == 0:
            dbg("Responding to setup.xml for %s" % self.name)
            xml = SETUP_XML % {'device_name': self.name, 'device_serial': self.serial}
            date_str = format_timetuple_and_zone(clock.gmtime(), 'GMT')
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
                self.relayState = 1
                success = self.action_handler.on()
            elif data.find(b'<BinaryState>0</BinaryState>') != -1:
                # off
                dbg("Responding to OFF for %s" % self.name)
                self.relayState = 0
                success = self.action_handler.off()
            else:
                dbg("Unknown Binary State request:")

            if success:
                state = self.getState()
                soap = GetBinaryState_soap % {'state_realy': state}
                date_str = format_timetuple_and_zone(clock.gmtime(), 'GMT')
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

    def getState(self):
        return self.relayState


class upnp_broadcast_responder:
    """
     Since we have a single process managing several virtual UPnP devices,
     we only need a single listener for UPnP broadcasts. When a matching
     search is received, it causes each device instance to respond.
     Note that this is currently hard-coded to recognize only the search
     from the Amazon Echo for WeMo devices. In particular, it does not
     support the more common root device general search. The Echo
     doesn't search for root devices.
    """
    TIMEOUT = 0
    inprogress = False

    def __init__(self):
        self.devices = []

    def init_socket(self):
        ok = True
        self.ip = '239.255.255.250'
        self.port = 1900
        try:
            # This is needed to join a multicast group
            self.mreq = struct.pack("4sl", inet_aton(self.ip), INADDR_ANY)
            # Set up server socket
            self.ssock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.ssock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                self.ssock.bind(('', self.port))
            except Exception as e:
                dbg("WARNING: Failed to bind %s:%d: %s", (self.ip, self.port, e))
                ok = False
            try:
                dbg("IP: " + str(socket.IPPROTO_IP) + " IP_ADD_MEMBERSHIP: " + str(socket.IP_ADD_MEMBERSHIP) + " mreq: " + str(self.mreq) )
                self.ssock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, self.mreq)
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
            # Issue https://github.com/kakopappa/arduino-esp8266-alexa-multiple-wemo-switch/issues/22
            if data.find(b'M-SEARCH') == 0 and self.inprogress is False:
                if data.find(b'upnp:rootdevice') != -1 or data.find(b'ssdp:all') != -1 or data.find(b'urn:Belkin:device:**') != -1:
                    for device in self.devices:
                        time.sleep(0.5)
                        device.respond_to_search(sender, 'urn:Belkin:device:**') #(sender, 'upnp:rootdevice')?
                        self.inprogress = True
                else:
                    pass
            else:
                pass

    # Receive network data
    def recvfrom(self, size):
        if self.TIMEOUT:
            self.ssock.setblocking(0)
            ready = select.select([self.ssock], [], [], self.TIMEOUT)[0]
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


class rest_api_handler(object):
    """
     This is an example handler class. The fauxmo class expects handlers to be
     instances of objects that have on() and off() methods that return True
     on success and False otherwise.

     This example class takes a color and brightness.
     It returns always True and ignores any return data.
    """
    def __init__(self, on_color, on_brightness):
        global ledNumber
        global ws2812_chain
        self.on_color = on_color
        self.on_brightnessr = on_brightness
        ws2812_chain.set_brightness(on_brightness)

    def on(self):
        global ledNumber
        global ws2812_chain
        # global_epoch = timeutils.epoch() # updating time using ntp
        data = [self.on_color for i in range(ledNumber)]
        ws2812_chain.show(data)
        dbg("response on")
        return True

    def off(self):
        global ledNumber
        global ws2812_chain
        # global_epoch = timeutils.epoch() # updating time using ntp
        data = [(0, 0, 0) for i in range(ledNumber)]
        ws2812_chain.show(data)
        dbg("response off")
        return True


class InvalidPortException(Exception):
    # Exception definitions that are used in the package
    pass


def thread_echo(args):
    global DEBUG
    global clock
    global ws2812_chain
    # Set up our singleton for polling the sockets for data ready

    ws2812_chain = WS2812(ledNumber=ledNumber, brightness=100)
    p = poller()

    """
     Each entry is a list with the following elements:

     # name of the virtual switch
     # handler object with 'on' and 'off' methods (e.g. rest_api_handler((rrr, ggg, bbb), lux)})
     # port #

     NOTE: As of 2015-08-17, the Echo appears to have a hard-coded limit of
     16 switches it can control. Only the first 16 elements of the 'devices'
     list will be used.
     NOTE: Micropython has a limitation in the number of opened sockets (8).
     Then, the maximal device number is limited to 3.
    """
    devices = [
        {"description": "white led",
         "port": 12340,
         "handler": rest_api_handler((255, 255, 255), 50)},
        {"description": "red led",
         "port": 12341,
         "handler": rest_api_handler((255, 0, 0), 50)},
        {"description": "blue led",
         "port": 12342,
         "handler": rest_api_handler((30, 144, 255), 90)},
        # {"description": "green led",
        #  "port": 12343,
        #  "handler": rest_api_handler((0, 255, 0), 90)},
        # {"description": "orange led",
        #  "port": 12344,
        #  "handler": rest_api_handler((255, 165, 0), 90)}
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
        # if `port` doesn't exist, populate it
        # if it isnt an int, flip out with a descriptive exception
        if not device.get("port"):
            device["port"] = 0
        elif type(device["port"]) is not int:
            raise InvalidPortException("Invalid port of type: {}, with a value of: {}".format(type(device["port"]), device["port"]))
        fauxmo(device["description"], u, p, None, device["port"], action_handler=device["handler"])

    # setting the clock using ntp
    if uname().machine == 'WiPy with ESP32':
        # Wipy 2.0
        clock_tmp = RTC()
        clock_tmp.ntp_sync('time1.google.com')
        clock = time    #gmtime function needed
    elif uname().machine == 'ESP32 module with ESP32':
        # Wemos ESP-WROOM-32
        clock = RTC()   #gmtime function needed
        clock.ntp_sync('time1.google.com')

    dbg("Entering main loop\n")
    while True:
        try:
            # Allow time for a ctrl-c to stop the process
            p.poll(10)
            time.sleep(0.1)
            gc.collect()
        except Exception as e:
            dbg(e)
            # break


if thread_available:
    print("Starting echo serviceList on separated thread\n")
    _thread.start_new_thread(thread_echo, ('',))
else:
    print("Starting echo services\n")
    thread_echo('')

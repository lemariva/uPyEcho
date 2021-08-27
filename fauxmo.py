from upnp_device import UpnpDevice
from xmls import GET_BINARY_STATE_SOAP, EVENT_SERVICE_XML, SETUP_XML
from helpers import dbg, format_timetuple_and_zone, clock

class Fauxmo(UpnpDevice):
    '''
     This subclass does the bulk of the work to mimic a WeMo switch on the network.
    '''

    @staticmethod
    def make_uuid(name):
        return "".join(
            ["%x" % sum([ord(c) for c in name])]
            + ["%x" % ord(c) for c in "%sFauxmo!" % name]
        )[:14]

    def __init__(self, name, listener, poller, ip_address, port, action_handler=None):
        self.serial = self.make_uuid(name)
        self.name = name
        self.ip_address = ip_address
        self.relayState = 0
        persistent_uuid = "Socket-1_0-" + self.serial
        other_headers = ["X-User-Agent: redsonic"]
        UpnpDevice.__init__(
            self,
            listener,
            poller,
            port,
            "http://%(ip_address)s:%(port)s/setup.xml",
            "Unspecified, UPnP/1.0, Unspecified",
            persistent_uuid,
            other_headers=other_headers,
            ip_address=ip_address,
        )
        if action_handler:
            self.action_handler = action_handler
        else:
            self.action_handler = self
        dbg(
            "Fauxmo device '%s' ready on %s:%s"
            % (self.name, self.ip_address, self.port)
        )

    def get_name(self):
        return self.name

    def handle_request(self, data, sender, socket):
        if (
            data.find(b"POST /upnp/control/basicevent1 HTTP/1.1") == 0
            and data.find(b"urn:Belkin:service:basicevent:1#GetBinaryState") != -1
        ):
            state = self.getState()
            soap = GET_BINARY_STATE_SOAP % {"state_realy": state}
            date_str = format_timetuple_and_zone(clock.gmtime(), "GMT")
            message = (
                "HTTP/1.1 200 OK\r\n"
                "CONTENT-LENGTH: %d\r\n"
                'CONTENT-TYPE: text/xml charset="utf-8"\r\n'
                "DATE: %s\r\n"
                "EXT:\r\n"
                "SERVER: Unspecified, UPnP/1.0, Unspecified\r\n"
                "X-User-Agent: redsonic\r\n"
                "CONNECTION: close\r\n"
                "\r\n"
                "%s" % (len(soap), date_str, soap)
            )
            socket.send(message)
        elif data.find(b"GET /eventservice.xml HTTP/1.1") == 0:
            dbg("Responding to eventservice.xml for %s" % self.name)
            date_str = format_timetuple_and_zone(clock.gmtime(), "GMT")
            message = (
                "HTTP/1.1 200 OK\r\n"
                "CONTENT-LENGTH: %d\r\n"
                "CONTENT-TYPE: text/xml\r\n"
                "DATE: %s\r\n"
                "LAST-MODIFIED: Sat, 01 Jan 2000 00:01:15 GMT\r\n"
                "SERVER: Unspecified, UPnP/1.0, Unspecified\r\n"
                "X-User-Agent: redsonic\r\n"
                "CONNECTION: close\r\n"
                "\r\n"
                "%s" % (len(EVENT_SERVICE_XML), date_str, EVENT_SERVICE_XML)
            )
            socket.send(message)
        elif data.find(b"GET /setup.xml HTTP/1.1") == 0:
            dbg("Responding to setup.xml for %s" % self.name)
            xml = SETUP_XML % {"device_name": self.name, "device_serial": self.serial}
            date_str = format_timetuple_and_zone(clock.gmtime(), "GMT")
            message = (
                "HTTP/1.1 200 OK\r\n"
                "CONTENT-LENGTH: %d\r\n"
                "CONTENT-TYPE: text/xml\r\n"
                "DATE: %s\r\n"
                "LAST-MODIFIED: Sat, 01 Jan 2000 00:01:15 GMT\r\n"
                "SERVER: Unspecified, UPnP/1.0, Unspecified\r\n"
                "X-User-Agent: redsonic\r\n"
                "CONNECTION: close\r\n"
                "\r\n"
                "%s" % (len(xml), date_str, xml)
            )
            socket.send(message)
        elif (
            data.find(b'SOAPACTION: "urn:Belkin:service:basicevent:1#SetBinaryState"')
            != -1
        ):
            success = False
            if data.find(b"<BinaryState>1</BinaryState>") != -1:
                # on
                dbg("Responding to ON for %s" % self.name)
                self.relayState = 1
                success = self.action_handler.on()
            elif data.find(b"<BinaryState>0</BinaryState>") != -1:
                # off
                dbg("Responding to OFF for %s" % self.name)
                self.relayState = 0
                success = self.action_handler.off()
            else:
                dbg("Unknown Binary State request:")

            if success:
                state = self.getState()
                soap = GET_BINARY_STATE_SOAP % {"state_realy": state}
                date_str = format_timetuple_and_zone(clock.gmtime(), "GMT")
                message = (
                    "HTTP/1.1 200 OK\r\n"
                    "CONTENT-LENGTH: %d\r\n"
                    'CONTENT-TYPE: text/xml charset="utf-8"\r\n'
                    "DATE: %s\r\n"
                    "EXT:\r\n"
                    "SERVER: Unspecified, UPnP/1.0, Unspecified\r\n"
                    "X-User-Agent: redsonic\r\n"
                    "CONNECTION: close\r\n"
                    "\r\n"
                    "%s" % (len(soap), date_str, soap)
                )
                socket.send(message)
        else:
            dbg(data)

    def on(self):
        return False

    def off(self):
        return True

    def getState(self):
        return self.relayState
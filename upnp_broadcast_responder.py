from helpers import inet_aton, dbg
from global_data import *
try:
    import ustruct as struct
except:
    import struct
try:
    import usocket as socket
except:
    import socket

class UpnpBroadcastResponder:
    '''
     Since we have a single process managing several virtual UPnP devices,
     we only need a single listener for UPnP broadcasts. When a matching
     search is received, it causes each device instance to respond.
     Note that this is currently hard-coded to recognize only the search
     from the Amazon Echo for WeMo devices. In particular, it does not
     support the more common root device general search. The Echo
     doesn't search for root devices.
    '''

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
                self.ssock.bind(("", self.port))
            except Exception as e:
                dbg("WARNING: Failed to bind %s:%d: %s", (self.ip, self.port, e))
                ok = False
            try:
                dbg(
                    "IP: "
                    + str(socket.IPPROTO_IP)
                    + " IP_ADD_MEMBERSHIP: "
                    + str(socket.IP_ADD_MEMBERSHIP)
                    + " mreq: "
                    + str(self.mreq)
                )
                self.ssock.setsockopt(
                    socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, self.mreq
                )
            except Exception as e:
                dbg("WARNING: Failed to join multicast group!: " + str(e))
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
            if data.find(b"M-SEARCH") == 0 and self.inprogress is False:
                if (
                    data.find(b"upnp:rootdevice") != -1
                    or data.find(b"ssdp:all") != -1
                    or data.find(b"urn:Belkin:device:**") != -1
                ):
                    for device in self.devices:
                        time.sleep(0.5)
                        device.respond_to_search(
                            sender, "urn:Belkin:device:**"
                        )  # (sender, 'upnp:rootdevice')?
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

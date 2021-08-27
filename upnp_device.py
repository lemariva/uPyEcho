
import network
from helpers import dbg, format_timetuple_and_zone
import machine
try:
    import usocket as socket
except:
    import socket

class UpnpDevice:
    '''
     Base class for a generic UPnP device. This is far from complete
     but it supports either specified or automatic IP address and port
     selection.
    '''

    this_host_ip = None

    @staticmethod
    def local_ip_address():
        if not UpnpDevice.this_host_ip:
            try:
                ap_if = network.WLAN()
                UpnpDevice.this_host_ip = ap_if.ifconfig()[0]
            except:
                UpnpDevice.this_host_ip = "127.0.0.1"
            dbg("got local address of %s" % UpnpDevice.this_host_ip)
        return UpnpDevice.this_host_ip

    def __init__(
        self,
        listener,
        poller,
        port,
        root_url,
        server_version,
        persistent_uuid,
        other_headers=None,
        ip_address=None,
    ):
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
            self.ip_address = UpnpDevice.local_ip_address()

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
        date_str = format_timetuple_and_zone(clock.gmtime(), "GMT")
        location_url = self.root_url % {
            "ip_address": self.ip_address,
            "port": self.port,
        }
        message = (
            "HTTP/1.1 200 OK\r\n"
            "CACHE-CONTROL: max-age=86400\r\n"
            "DATE: %s\r\n"
            "EXT:\r\n"
            "LOCATION: %s\r\n"
            'OPT: "http://schemas.upnp.org/upnp/1/0/"; ns=01\r\n'
            "01-NLS: %s\r\n"
            "SERVER: %s\r\n"
            "ST: %s\r\n"
            "USN: uuid:%s::%s\r\n"
            "X-User-Agent: redsonic\r\n\r\n"
            % (
                date_str,
                location_url,
                self.uuid,
                self.server_version,
                search_target,
                self.persistent_uuid,
                search_target,
            )
        )

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

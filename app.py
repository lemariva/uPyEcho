import time
try:
    from machine import RTC
    if not hasattr(RTC, 'ntp_sync'):
        from ESP32MicroPython.timeutils import RTC
except:
    from ESP32MicroPython.timeutils import RTC
from wipyWS2812.ws2812 import WS2812
from poller import Poller
from upnp_broadcast_responder import UpnpBroadcastResponder
from helpers import dbg, clock
from devices import devices
from global_data import ledNumber
from fauxmo import Fauxmo
from uos import uname
import gc

class InvalidPortException(Exception):
    # Exception definitions that are used in the package
    pass

class App:
    def __init__(self):
        self.pooler = Pooler()
        self.upnp = UpnpBroadcastResponder()
        self.upnp.init_socket()
        self.pooler.add(self.upnp)

        for device in devices:
            if not device.get('port'):
                device['port'] = 0
            elif not isinstance(device['port'], int):
                raise InvalidPortException('Invalid port of type: {}, with a value of: {}'.format(type(device['port']), device['port']))
            Fauxmo(device['description'],u ,p, None, device['port'], action_handler=device['handler'])


    def thread_echo(self, args):
        global ws2812_chain
        dbg('Entering main loop\n')
        while True:
            try:
                # Allow time for a ctrl-c to stop the process
                self.pooler.poll(10)
                time.sleep(0.1)
                gc.collect()
            except Exception as e:
                dbg(e)
                break

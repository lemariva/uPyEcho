import time
try:
    from machine import RTC
    if not hasattr(RTC, "ntp_sync"):
        from ESP32MicroPython.timeutils import RTC
except:
    from ESP32MicroPython.timeutils import RTC
from wipyWS2812.ws2812 import WS2812
from poller import Poller
from upnp_broadcast_responder import UpnpBroadcastResponder
from rest_api_handler import RestApiHandler
from helpers import dbg
from devices import devices
from global_data import ledNumber
from fauxmo import Fauxmo
from uos import uname
import gc

class InvalidPortException(Exception):
    # Exception definitions that are used in the package
    pass

def thread_echo(args):
    global DEBUG
    global clock
    global ws2812_chain
    # Set up our singleton for polling the sockets for data ready

    ws2812_chain = WS2812(ledNumber=ledNumber, brightness=100)
    p = Poller()

    u = UpnpBroadcastResponder()
    u.init_socket()
    p.add(u)

    for device in devices:
        if not device.get("port"):
            device["port"] = 0
        elif type(device["port"]) is not int:
            raise InvalidPortException(
                "Invalid port of type: {}, with a value of: {}".format(
                    type(device["port"]), device["port"]
                )
            )
        Fauxmo(
            device["description"],
            u,
            p,
            None,
            device["port"],
            action_handler=device["handler"],
        )

    # setting the clock using ntp
    if uname().machine == "WiPy with ESP32":
        # Wipy 2.0
        clock_tmp = RTC()
        clock_tmp.ntp_sync("time1.google.com")
        clock = time  # gmtime function needed
    elif uname().machine == "ESP32 module with ESP32":
        # Wemos ESP-WROOM-32
        clock = RTC()  # gmtime function needed
        clock.ntp_sync("time1.google.com")

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

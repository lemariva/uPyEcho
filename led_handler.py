from  global_data import *
import machine

class LedHandler(object):

    def __init__(self):
        self.led = machine.Pin(15, machine.Pin.OUT, value=1)

    def on(self):
        self.led.on()
        return True

    def off(self):
        self.led.off()
        return True
from  global_data import *

class RestApiHandler(object):
    '''
     This is an example handler class. The Fauxmo class expects handlers to be
     instances of objects that have on() and off() methods that return True
     on success and False otherwise.

     This example class takes a color and brightness.
     It returns always True and ignores any return data.
    '''

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

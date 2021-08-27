from wipyWS2812.ws2812 import WS2812

DEBUG = True
INADDR_ANY = 0
global_epoch = 0  # time over ntp-server

# W2812b
ledNumber = 144  # number of leds
chain = []
#clock = None

ws2812_chain = WS2812(ledNumber=ledNumber, brightness=100)
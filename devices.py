from rest_api_handler import RestApiHandler
from led_handler import LedHandler

'''
    Each entry is a list with the following elements:

    # name of the virtual switch
    # handler object with 'on' and 'off' methods (e.g. RestApiHandler((rrr, ggg, bbb), lux)})
    # port #

    NOTE: As of 2015-08-17, the Echo appears to have a hard-coded limit of ftp access from ftp import ftpserver

    16 switches it can control. Only the first 16 elements of the 'devices'
    list will be used.
    NOTE: Micropython has a limitation in the number of opened sockets (8).
    Then, the maximal device number is limited to 3.
'''
devices = [
    {
        "description": "led",
        "port": 12340,
        "handler": LedHandler(),
    },
    {
        "description": "red led",
        "port": 12341,
        "handler": RestApiHandler((255, 0, 0), 50),
    },
    # {
    #     "description": "blue led",
    #     "port": 12342,
    #     "handler": RestApiHandler((30, 144, 255), 90),
    # },
    # {
    #     "description": "green led",
    #     "port": 12343,
    #     "handler": RestApiHandler((0, 255, 0), 90),
    # },
    # {
    #     "description": "orange led",
    #     "port": 12344,
    #     "handler": RestApiHandler((255, 165, 0), 90),
    # },
]
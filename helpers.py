from global_data import DEBUG
from uos import uname
try:
    from machine import RTC
    if not hasattr(RTC, "ntp_sync"):
        from ESP32MicroPython.timeutils import RTC
except:
    from ESP32MicroPython.timeutils import RTC
import time

def dbg(msg):
    global DEBUG
    if DEBUG:
        print(msg)

def inet_aton(addr):
    ip_as_bytes = bytes(map(int, addr.split('.')))
    return ip_as_bytes

def format_timetuple_and_zone(timetuple, zone):
    return '%s, %02d %s %04d %02d:%02d:%02d %s' % (
        ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][timetuple[6]],
        timetuple[2],
        [
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep',
            'Oct',
            'Nov',
            'Dec',
        ][timetuple[1] - 1],
        timetuple[0],
        timetuple[3],
        timetuple[4],
        timetuple[5],
        zone,
    )

def get_clock():
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
    return clock

clock = get_clock()
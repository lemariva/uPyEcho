from global_data import DEBUG

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
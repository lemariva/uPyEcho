try:
    import usocket as socket
except:
    import socket
import uselect as select
from helpers import dbg

class Poller:
    # A simple utility class to wait for incoming data to be
    # read on a socket.
    def __init__(self):
        if "poll" in dir(select):
            self.use_poll = True
            self.poller = select.poll()
        else:
            self.use_poll = False
        self.targets = {}

    def add(self, target, socket=None):
        if not socket:
            socket = target.sockets()
        if self.use_poll:
            self.poller.register(socket, select.POLLIN)
        # dbg("add device on fileno: %s" % socket.fileno() )
        self.targets[socket.fileno()] = target
        # dbg("size targets: %s" % len(self.targets))

    def remove(self, target, socket=None):
        if not socket:
            socket = target.sockets()
        if self.use_poll:
            self.poller.unregister(socket)
        # dbg("remove device on fileno: %s" % socket.fileno() )
        gc.collect()

    def poll(self, timeout=100):
        if self.use_poll:
            ready = self.poller.poll(timeout)
        else:
            ready = []
            if len(self.targets) > 0:
                (rlist, wlist, xlist) = select.select(
                    self.targets.keys(), [], [], timeout
                )
                ready = [(x, None) for x in rlist]

        for one_ready in ready:
            target = self.targets.get(one_ready[0].fileno(), None)
            dbg("Targets %s" % str(self.targets.keys()))
            if target:
                # dbg("get socket with fileno: %s" % str(one_ready[0].fileno()) +  " len: %s" % len(one_ready) + " selected: %s " % str(target.fileno()) )
                # update time
                target.do_read(one_ready[0])

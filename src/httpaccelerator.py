import os
import sys
import mmap
from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList
from twisted.python.failure import Failure
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from optparse import OptionParser

class ReceiveURLPart(Protocol):
    def __init__(self, finished, mmap, offset):
        self.mmap = mmap
        self.finished = finished
        self.offset = offset

    def dataReceived(self, bytes):
        self.mmap[self.offset:self.offset+len(bytes)] = bytes
        self.offset+=len(bytes)

    def connectionLost(self, reason):
        print "Finished receiving body:", reason.getErrorMessage()
        print "Received %d bytes" % self.offset
        self.finished.callback(None)

class URLPartRetreiver(object):
    def __init__(self, reactor, out, url, content_length, instance, num_instances):
        self.reactor = reactor
        self.out = out
        self.url = url
        self.content_length = content_length,
        self.instance = instance

        bytes_per_instance = content_length / num_instances
        self.startbyte = instance*bytes_per_instance
        self.endbyte = self.startbyte + bytes_per_instance - 1
        if self.instance == num_instances - 1:
            self.endbyte = content_length - 1

    def get(self):
        d = Agent(self.reactor).request("GET", self.url,
                                        Headers({'Range':["bytes=%d-%d" % (self.startbyte, self.endbyte)]}))
        d.addCallback(self.cb_get)
        return d

    def cb_get(self, response):
        finished = Deferred()
        print "cb_get", self.instance, response.code
        response.deliverBody(ReceiveURLPart(finished, self.out, self.startbyte))
        return finished
                      

class HTTPAccelerator(object):
    def __init__(self, url, num_connections=5, _reactor=None):
        self.url = url
        self.num_connections = 5
        self.manage_reactor = False
        if _reactor != None:
            self.reactor = _reactor
        else:
            self.reactor = reactor
            self.manage_reactor = True

    def save_url(self):
        agent = Agent(self.reactor)
        d = agent.request('HEAD',
                          self.url)
        d.addCallback(self.cb_head)
        d.addBoth(self.cb_shutdown)

        if self.manage_reactor:
            self.reactor.run()

    def cb_head(self, response):
        print "response code", response.code
        self.content_length = int(response.headers.getRawHeaders("Content-Length")[0])
        print "Content length is", self.content_length

        self.fd = os.open("/tmp/dl-out", os.O_RDWR|os.O_CREAT|os.O_TRUNC, 0600)
        os.lseek(self.fd, self.content_length-1, os.SEEK_SET)
        os.write(self.fd, "\0")

        self.mmap = mmap.mmap(self.fd, self.content_length, prot=mmap.PROT_WRITE|mmap.PROT_READ)

        dl = DeferredList([URLPartRetreiver(self.reactor, self.mmap, self.url,
                                              self.content_length, num, self.num_connections).get() for num in range(self.num_connections)])
        dl.addCallback(self.all_finished)
        return dl

    def all_finished(self, arg):
        print "All finished, flushing"
        self.mmap.flush()
        print "Flushed, closing"
        os.close(self.fd)
        print "Closed"

        


    def cb_shutdown(self, arg):
        if isinstance(arg, Failure):
            print >> sys.stderr, arg
        if self.manage_reactor:
            self.reactor.stop()

                          

def run():
    optparse = OptionParser(usage="%prog [url]")
    optparse.add_option("-n", help="# of parallel connections", type="int", default=5, dest="num_connections")

    (options, args) = optparse.parse_args()

    if len(args) < 1:
        optparse.print_help()
        sys.exit(1)

    url = args[0]

    ha = HTTPAccelerator(url, options.num_connections)
    ha.save_url()

    
    
    

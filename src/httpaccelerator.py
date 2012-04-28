import sys
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from optparse import OptionParser

class ReceiveURLPart(Protocol):
    def __init__(self, finished, size):
        self.finished = finished
        self.remaining = size

    def dataReceived(self, bytes):
        self.remaining-=len(bytes)
        print "Received %d bytes, %d remaining" % (len(bytes), self.remaining)

    def connectionLost(self, reason):
        print "Finished receiving body:", reason.getErrorMessage()
        self.finished.callback(None)

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

        agent = Agent(self.reactor)
        d = agent.request("GET", self.url)
        d.addCallback(self.cb_get)
        return d

    def cb_get(self, response):
        finished = Deferred()
        response.deliverBody(ReceiveURLPart(finished, self.content_length))
        return finished

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

    
    
    

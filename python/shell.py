"""
A shell useful while testing ezgliding functionality.

It provides an Cmd based shell to easily trigger each function.
"""
import cmd
import logging
import readline
import urllib2
import subprocess
import sys
import traceback

import crawler
import flight
import optimizer

def getTraceback():
    """
    Returns a simplified stack trace for logging.
    """
    cla, exc, trbk = sys.exc_info()
    return "Class: '%s' :: Exception: '%s' :: Traceback: '%s'" \
        % (cla.__name__, exc, traceback.format_tb(trbk, 5))

class Command(cmd.Cmd):
    """
    A Cmd implementation exposing all ezgliding functionality.

    Useful for testing purposes.
    """
    def __init__(self):
        cmd.Cmd.__init__(self)

        logging.basicConfig(level=logging.DEBUG)

        self.flight = None
        self.prompt = "ezgliding> "
        self.intro = """
The ezgliding.com software shell.
            
It provides commands exposing all functionality, especially useful for 
testing purposes. Type 'help' or 'help command' for more information.
"""

    def do_crawl(self, crawlType):
        """
        Invokes the given crawler and lists the corresponding flights.

        Existing crawlers include: netcoupe
        """
        try:
            crawl = crawler.NetcoupeCrawler()
            flights = crawl.crawl(crawl.lastProcessedId())
            for flight in flights:
                crawl.processFlight(flight[0], flight[2])
        except:
            logging.error("Failed to crawl flights :: %s" % getTraceback())

    def do_load(self, paramStr):
        """
        Loads the given flight into memory, so that you can issue other 
        commands like optimize, etc.

        Parameters are flightId and crawlType (optional, default is netcoupe).

        example: load 30604 netcoupe
        """
        params = paramStr.split(" ")
        if len(params) == 1:
            params.append("netcoupe")

        try:
            crawl = None
            if params[1] == "netcoupe":
                crawl = crawler.NetcoupeCrawler()
            else:
                logging.error("Unknown crawlType given :: %s" % params[1])
                return
            self.flight = crawl.getFlight(int(params[0]))
            if self.flight is None:
                logging.error("Failed to load: crawltype %s has no flight %s" 
                        % (params[1], params[0]))
        except:
            logging.error("Failed to load :: %s" % getTraceback())

    def do_lload(self, location):
        """
        Loads the flight track at the given location.

        The location is an URI, file:/// can be used for local files.
        """
        try:
            track = urllib2.urlopen(location)
            data = track.read()
            track.close()
            parser = flight.FlightParser(data)
            self.flight = parser.flight
        except:
            logging.error("Failed to load track :: %s" % getTraceback())

    def do_optimize(self, optType):
        """
        Optimizes the currently loaded flight, printing the result. It accepts
        the optimization type to be used - current types are:
        1 - out and return
        2 - two turnpoints (triangle)
        3 - three turnpoints (netcoupe style)

        If no type is specified, then all optimizations are performed.

        example: optimize 3

        TODO: FAI triangle, 4 turnpoints (olc style)
        """
        optType = int(optType) if optType != "" else 2

        if self.flight is not None:
            try:
                ezopt = optimizer.Optimizer(self.flight)
                optMethod = getattr(ezopt, "optimize%s" % optType)
                optMethod()
            except:
                logging.error("Failed to optimize :: %s" % getTraceback())

    def do_print(self, command):
        """
        Prints details of the currently loaded flight (if any).
        """
        if self.flight is not None:
            logging.info(self.flight)

    def do_exit(self, value):
        """
        Quits the shell.
        """
        return self.do_quit(value)

    def do_quit(self, value):
        """
        Quits the shell.
        """
        return True

    def do_shell(self, command):
        """
        Executes the given shell command.
        """
        try:
            subprocess.check_call(command.split(' '))
        except:
            logging.error("Failed to execute command '%s' :: %s" % (command,
                getTraceback()))

    def do_help(self, command):
        """
        Lists available commands - help <command> for command details.
        """
        cmd.Cmd.do_help(self, command)

if __name__ == "__main__":
    ezglider = Command()
    ezglider.cmdloop()

import cmd
import readline
import urllib2
import sys

import flight
import optimizer

class Command(cmd.Cmd):

    def __init__(self):
        cmd.Cmd.__init__(self)
        self.flight = None
        self.prompt = "ezgliding> "
        self.intro = """
The ezgliding.com software shell.
            
It provides commands exposing all functionality, especially useful for 
testing purposes. Type 'help' or 'help command' for more information.
"""

    def do_load(self, location):
        """
        Loads the given flight into memory, so that you can issue other 
        commands like optimize, etc.

        example: load http://ezgliding.com/path/to/flight 
        (for local files use file:///path/to/file)
        """
        try:
            uri = urllib2.urlopen(location)
            data = uri.read()
            uri.close()
            self.flight = flight.FlightParser(data).flight
        except:
            print "Failed to load :: ", sys.exc_info()[1]

    def do_optimize(self, optType=2):
        """
        Optimizes the currently loaded flight, printing the result. It accepts
        the optimization type to be used - current types are:
        1 - out and return
        2 - two turnpoints (triangle)
        3 - three turnpoints (netcoupe style)

        example: optimize 3

        TODO: FAI triangle, 4 turnpoints (olc style)
        """

        if self.flight is not None:
            try:
                ezopt = optimizer.Optimizer(self.flight)
                optMethod = getattr(ezopt, "optimize%s" % optType)
                optMethod()
            except:
                print "Failed to optimize :: ", sys.exc_info()[1]

    def do_print(self, command):
        """
        Prints details of the currently loaded flight (if any).
        """
        if self.flight is not None:
            print self.flight

    def do_exit(self, value):
        """
        Quits the shell.
        """
        self.do_quit(value)

    def do_quit(self, value):
        """
        Quits the shell.
        """
        return True

    def do_shell(self):
        """
        Executes the given shell command.
        """
        None

    def do_help(self, command):
        """
        Lists available commands - help <command> for command details.
        """
        cmd.Cmd.do_help(self, command)

if __name__ == "__main__":
    ezglider = Command()
    ezglider.cmdloop()

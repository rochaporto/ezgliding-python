import logging
import urllib2
import sys

from google.appengine.api import taskqueue, urlfetch
from google.appengine.ext.webapp import RequestHandler, WSGIApplication
from google.appengine.ext.webapp.util import run_wsgi_app

import appdata
from igc import FlightParser, FlightExporter

class CommonHandler(RequestHandler):

    gAuthUri = "https://www.google.com/accounts/ClientLogin"

    fusionTablesUri = "http://www.google.com/fusiontables/api/query"

    def __init__(self):
        None

    def gAuth(self, username, password, service, accountType):
        authData = urllib.urlencode(
                {"Email": username, "Passwd": password, "service": service, 
                "accountType": accountType})
        authReq = urllib2.Request(self.gAuthUri, data=authData)
        authResp = urllib2.urlopen(authReq).read()
        authDict = dict(x.split("=") for x in authResp.split("\n") if x)
        return authDict["Auth"]

class NetcoupeHandler(CommonHandler):
    """
    The RequestHandler used as a cron job to fetch flights from
    the netcoupe.net competition.
    """

    def lastProcessedId(self):
        """
        Returns the last flight ID already fetched and processed.
        """
        return 36233

    def getTask(self, flightId, url):
        """
        Returns a Task object with all the given data in the expected places,
        ready to be added to its queue.
        """
        task = taskqueue.Task(
                url="/crawler/netcoupe/worker", 
                params={"id": flightId, "url": url})
        return task

    def queueFlights(self, startId=1, lastId=-1):
        """
        Queues the flights corresponding to the given IDs for later
        processing, validating that the flights actually exist in the
        netcoupe competition.
        """
        curId = startId
        while True:
            flightUrl = NetcoupeWorker._baseIgcUrl % curId
            result = urlfetch.fetch(flightUrl)
            flightData = result.content
            if len(flightData) == 0 or (lastId != -1 and curId > lastId):
                logging.info("stopping flight queueing at ID %d" % curId)
                break
            self.getTask(curId, flightUrl).add("crawler-netcoupe")

            logging.info("queued for processing ID %d" % curId)
            curId = curId + 1

    def get(self):
        """
        This is the method called by the appengine Handler.
        """
        self.queueFlights(self.lastProcessedId())

class NetcoupeWorker(CommonHandler):
    """
    The RequestHandler picking up tasks from the netcoupe.net competition
    queue, processing them, and pushing the result into the fusion table.
    """

    _baseDetailUrl = "http://netcoupe.net/Results/FlightDetail.aspx?FlightID=%s"
    _baseIgcUrl = "http://netcoupe.net/Download/DownloadIGC.aspx?FileID=%s"

    def __init__(self):
        self.authToken = None

    def netcoupeData(self, flightId):
        """
        Returns all the netcoupe defined data (info separated from the stuff
        in the igc file, which the netcoupe does not necessarily use).
        """
        None

    def getFlight(self, flightId):
        """
        Returns a Flight object containing all the processed IGC data.
        """
        flightUrl = self._baseIgcUrl % flightId
        result = urlfetch.fetch(flightUrl)
        if result.status_code != 200:
            logging.error("Unexpected code %d processing flight %s" 
                    % (result.status_code, flightUrl))
        flightData = result.content
        try:
            reader = FlightParser(flightData)
        except:
            logging.error("failed processing flight :: %s" % (flightUrl))
            raise
        return reader.flight

    def processFlight(self, flightId):
        """
        Processes a single flight (the one from the given id).
        This includes both the IGC file data, and the netcoupe specific data
        taken from the webpage.
        """
        flight = self.getFlight(flightId)
        netcoupeData = self.netcoupeData(flightId)
        logging.info(flight)

    def post(self):
        """
        The RequestHandler method called by the task processing.
        """
        flightId = self.request.get("id")
        self.processFlight(flightId)
        #exporter = FlightExporter(reader.flight)
        #req = urllib2.Request(self.fusionTablesUri,
        #        urllib.urlencode({"sql": exporter.toFusionTable(872803)}),
        #        {"Authorization": "GoogleLogin auth=%s" % self.authToken,
        #        "Content-Type": "application/x-www-form-urlencoded"})
        #resp = urllib2.urlopen(req)

def main():
    app = WSGIApplication([
            ('/crawler/netcoupe', NetcoupeHandler),
            ('/crawler/netcoupe/worker', NetcoupeWorker),
            ], debug=True)
    logging.getLogger().setLevel(logging.DEBUG)
    run_wsgi_app(app)

if __name__ == '__main__':
    main()

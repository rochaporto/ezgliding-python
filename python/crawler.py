"""
Crawlers for flights available in online gliding competitions.

This modules provides flight crawlers for popular online gliding competitions.

These crawlers can both download the flights and save them.
"""
import logging
import urllib2
import sys

import appdata
import flight

class BaseCrawler(object):
    """
    Base class with common functionality to all handlers.

    Inheritance could be avoided if we made it a util class.
    """
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

class NetcoupeCrawler(BaseCrawler):
    """
    The RequestHandler used as a cron job to fetch flights from
    the netcoupe.net competition.
    """

    _baseDetailUrl = "http://netcoupe.net/Results/FlightDetail.aspx?FlightID=%s"
    _baseIgcUrl = "http://netcoupe.net/Download/DownloadIGC.aspx?FileID=%s"

    def lastProcessedId(self):
        """
        Returns the last flight ID already fetched and processed.
        """
        return 36261

    def crawl(self, startId=1, lastId=-1):
        """
        Returns IDs/URLs of new flights in the netcoupe competition.

        Flights are returned as tuples (ID, URL).

        Newer flights are any with an ID above lastProcessedId().
        """
        flights = []
        curId = startId
        while True:
            flightUrl = NetcoupeCrawler._baseIgcUrl % curId
            logging.debug("Fetching flight :: %s" % flightUrl)
            flight = urllib2.urlopen(flightUrl)
            flightData = flight.read()
            flight.close()
            if len(flightData) == 0 or (lastId != -1 and curId > lastId):
                logging.info("stopping flight queueing at ID %d" % curId)
                break
            flights.append((curId, flightUrl))
            curId = curId + 1

        return flights

    def getFlightData(self, flightId):
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
        flightD = urllib2.urlopen(flightUrl)
        flightData = flightD.read()
        flightD.close()
        if flightD.getcode() != 200:
            logging.error("Unexpected code %d processing flight %s" 
                    % (flightD.getcode(), flightUrl))
        try:
            reader = flight.FlightParser(flightData)
        except:
            logging.error("Failed processing flight :: %s" % sys.exc_info()[1])
            raise
        return reader.flight

    def processFlight(self, flightId):
        """
        Processes a single flight (the one from the given id).

        This includes parsing the track and fetching the netcoupe data.
        """
        flight = self.getFlight(flightId)
        netcoupeData = self.getFlightData(flightId)
        logging.info(flight)

"""
Crawlers for flights available in online gliding competitions.

This modules provides flight crawlers for popular online gliding competitions.

These crawlers can both download the flights and save them.
"""
import logging
import urllib2
import re
import sys

from BeautifulSoup import BeautifulSoup

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
    _baseFlightUrl = "http://netcoupe.net/Download/DownloadIGC.aspx?FileID=%s"

    def lastProcessedId(self):
        """
        Returns the last flight ID already fetched and processed.
        """
        return 30604

    def crawl(self, startId=1, lastId=-1):
        """
        Returns IDs/URLs of new flights in the netcoupe competition.

        Flights are returned as tuples (ID, URL).

        Newer flights are any with an ID above lastProcessedId().
        """
        flights = []
        curId = startId
        while True:
            flightUrl = NetcoupeCrawler._baseDetailUrl % curId
            # Check the detail page... if non existent then we're done
            logging.debug("Processing flight %d :: %s" % (curId, flightUrl))
            extra = self.getFlight(curId)
            if extra is None:
                logging.info("Stopping at flight %d :: %s" 
                        % (curId, flightUrl))
                break
            flights.append((curId, flightUrl, extra))
            # And we try the next id
            curId = curId + 1

        return flights

    def getFlight(self, flightId):
        """
        Returns all the netcoupe defined data (info separated from the stuff
        in the igc file, which the netcoupe does not necessarily use).
        """
        extra = None
        flightUrl = self._baseDetailUrl % flightId
        logging.debug("Fetching flight %d :: %s" % (flightId, flightUrl))

        dPage = urllib2.urlopen(flightUrl)
        extraData = dPage.read()
        dPage.close()

        if extraData.find("indisponible") != -1:
            logging.debug("Extra data for %d was empty" % flightId)
            return None

        # First parse the 'extra' flight metadata (netcoupe specific)
        soup = BeautifulSoup(extraData)
        items = soup.findAll("td")
        extra = {
            "name": items[4].div.a.string.strip(),
            "club": items[8].div.a.string.strip(),
            "date": items[12].div.string.strip(),
            "airfield": items[14].div.string.strip(),
            "country": items[18].div.string.strip(),
            "distance": float(
                items[20].div.string.replace('&nbsp;kms','').strip(' \r\n').replace(",",".")),
            "glider": items[25].string.replace('&nbsp;','').strip(),
            "fileid": int(re.match(r".*FileID=(\d+)", items[30].div.a["href"].strip()).groups()[0]),
            "avgSpeed": float(items[32].div.string.replace('&nbsp;km/h','').strip().replace(",",".")),
            "comment": items[44].div.string.strip(' \r\n'),
        }

        # Then parse the actual flight track
        flightUrl = self._baseFlightUrl % extra["fileid"]
        flightD = urllib2.urlopen(flightUrl)
        flightData = flightD.read()
        flightD.close()
        if flightD.getcode() != 200:
            logging.error("Unexpected code %d processing flight %s" 
                    % (flightD.getcode(), flightUrl))
        parser = flight.FlightParser(flightData, extra=extra)
        return parser.flight

    def processFlight(self, flightId, extra):
        """
        Processes a single flight (the one from the given id).

        This includes parsing the track and fetching the netcoupe data.
        """
        None

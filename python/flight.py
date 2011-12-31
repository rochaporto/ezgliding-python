import optparse
import sys

from datetime import datetime, timedelta
from math import sin, cos, asin, acos, atan2, fabs, sqrt, radians, degrees, pi

class FlightBase(object):
    """
    Base class providing utility functions.

    A 'util' class instead of inheritance might be simpler.
    """
    
    # FAI Earth Sphere Radius
    earthRadius = 6371 

    def __init__(self):
        None

    def dms2dd(self, value):
        """
        Converts coordinates from DMS to decimal format.
        """
        cardinal = value[-1]
        dd = None
        if cardinal in ('N', 'S'):
            dd = float(value[0:2]) + ( ( float(value[2:4]) + (float(value[4:7]) / 1000.0)) / 60.0 )
        else:
            dd = float(value[0:3]) + ( ( float(value[3:5]) + (float(value[5:8]) / 1000.0)) / 60.0 )
        if cardinal in ('S', 'W'):
            dd *= -1
        return dd

    def distance(self, p1, p2):
        """
        Returns the distance between the two given points.

        The distance is calculated as the great circle distance connecting the
        two points. The FAI earth radius is used as a basis.
        """
        return 2 * asin( 
                sqrt( (sin( (p1["latrd"] - p2["latrd"]) / 2 ) ) ** 2 
                    + cos(p1["latrd"]) * cos(p2["latrd"]) * ( sin( (p1["lonrd"] - p2["lonrd"]) / 2 ) ) ** 2
                    )
                ) * self.earthRadius

    def bearing(self, p1, p2):
        """
        Returns the bearing (in degrees) from point 1 to point 2.
        """
        return degrees(
                atan2( 
                    sin(p1["lonrd"] - p2["lonrd"]) * cos(p2["latrd"]), 
                    cos(p1["latrd"]) * sin(p2["latrd"]) 
                    - sin(p1["latrd"]) * cos(p2["latrd"]) * cos(p1["lonrd"] - p2["lonrd"])
                ) % (2 * pi)
                )

class Flight(FlightBase):
    """
    Class represent a flight as a set of consecutive points (lat/lon/alt).

    You can fill the flight using putPoint().

    self.metadata: flight metadata taken from the igc log or external sources
      dte (date), fxa (fix accuracy), plt (pilot), cm2 (crew 2), 
      gty (glider type), gid (glider reg number), dtm (gps datum), 
      rfw (logger firmware revision), rhw (logger revision number), 
      fty (logger mfr and model), gps (gps mfr / model),
      prs (pressure sensor description), cid (competition id), 
      ccl (glider class)

    self.control: control evaluation of circling, straight, start, etc
      minSpeed: used for flight start / end
      minCircleRate: 
      minCircleTime: min seconds for a spiral to have started
      minStraightTime: min seconds for a spiral to have ended

    self.points: points of the flight track (and point metadata)
      time: time of point measurement (down to second)
      lat: latitude (DMS)
      lon: longitude (DMS)
      fix:
      pAlt: pressure altitude
      gAlt: gps altitude
      (check methods computeL* for further point metadata)
      
    self.phases: the difference flight phases (circling, straight)

    self.stats: total flight stats
      totalKms: total kms (this will be a lot more than the optimized values)
      maxAlt: max altitude
      maxGSpeed: max ground speed
      minGSpeed: min ground speed
    """

    STOPPED, STRAIGHT, CIRCLING = range(3)

    def __init__(self):
        """
        Initiates the internal structures.
        """
        self.metadata = {
            "mfr": None, "mfrId": None, "mfrIdExt": None,
            "dte": None, "fxa": None, "plt": None, "cm2": None, "gty": None,
            "gid": None, "dtm": None, "rfw": None, "rhw": None, "fty": None,
            "gps": None, "prs": None, "cid": None, "ccl": None
        }
        self.control = {
            "minSpeed": 50.0, "minCircleRate": 4, "minCircleTime": 45, "minStraightTime": 15,
        }
        self.points = []
        self.phases = []
        self.stats = {
            "totalKms": 0.0, "maxAlt": None, "minAlt": None, "maxGSpeed": None, "minGSpeed": None,
        }

    def putPoint(self, time, lat, lon, fix, pAlt, gAlt):
        """
        Adds a new point to the flight track.

        In addition, it calculates all the derived metadata (calling the
        compute* methods).
        """
        p = {
            "time": time, "lat": lat, "lon": lon, "fix": fix, "pAlt": pAlt, "gAlt": gAlt,
            "latdg": None, "londg": None, "latrd": None, "lonrd": None,
            "computeL2": {
                "distance": None, "bearing": None, "timeDelta": None, "pAltDelta": None, "gAltDelta": None,
            },
            "computeL3": {
                "gSpeed": None, "pVario": None, "gVario": None, "turnRate": None,
            },
            "computeL4": {
                "mode": Flight.STOPPED,
            },
            }
        prevP = self.points[-1] if len(self.points) != 0 else None
        self.computeL1(p)
        if prevP is not None:
            self.computeL2(prevP, p)
            #self.computeL3(prevP, p)
            #self.computeStats(p)
        self.points.append(p)
        self.updateMode()

    def computeL1(self, p):
        """
        Computes all point metadata that does not require the previous point.
            (latdg, londg, latrd, lonrd) meaning degrees and radians
s
        """
        p["latdg"] = self.dms2dd(p["lat"])
        p["londg"] = self.dms2dd(p["lon"])
        p["latrd"] = radians(p["latdg"])
        p["lonrd"] = radians(p["londg"])

    def computeL2(self, prevP, p):
        """
        Computes point metadata only requiring the previous point.
          (distance, bearing, timeDelta, pAltDelta, gAltDelta)
        """
        p["computeL2"]["distance"] = self.distance(prevP, p)
        p["computeL2"]["bearing"] = self.bearing(prevP, p)
        p["computeL2"]["timeDelta"] = (p["time"] - prevP["time"]).seconds
        p["computeL2"]["pAltDelta"] = p["pAlt"] - prevP["pAlt"]
        p["computeL2"]["gAltDelta"] = p["gAlt"] - prevP["gAlt"]

    def computeL3(self, prevP, p):
        """
        Computes point metadata requiring previously computed values.
            (gSpeed, pVario, gVario, turnRate)
        """
        p["computeL3"]["gSpeed"] = (p["computeL2"]["distance"] * 3600) / p["computeL2"]["timeDelta"]
        p["computeL3"]["pVario"] = float(p["computeL2"]["pAltDelta"]) / p["computeL2"]["timeDelta"]
        p["computeL3"]["gVario"] = float(p["computeL2"]["gAltDelta"]) / p["computeL2"]["timeDelta"]
        if prevP["computeL2"]["bearing"] is not None:
            p["computeL3"]["turnRate"] = (p["computeL2"]["bearing"] \
                - prevP["computeL2"]["bearing"]) / p["computeL2"]["timeDelta"]

    def computeStats(self, p):
        """
        Updates the internal flight stats considering the new given point.
        """
        self.stats["totalKms"] += p["computeL2"]["distance"]
        self.stats["maxAlt"] = max(self.stats["maxAlt"], p["pAlt"])
        self.stats["minAlt"] = p["pAlt"] if self.stats["minAlt"] is None \
            else min(self.stats["minAlt"], p["pAlt"])
        self.stats["maxGSpeed"] = max(self.stats["maxGSpeed"], p["computeL3"]["gSpeed"])
        self.stats["minGSpeed"] = p["computeL3"]["gSpeed"] if self.stats["minGSpeed"] is None \
            else min(self.stats["minGSpeed"], p["computeL3"]["gSpeed"])

    def newPhase(self, pIndex, phaseType):
        """
        Adds a new flight phase to the phases list, closing the previous one.
        """
        if len(self.phases) != 0:
            self.phases[-1]["end"] = pIndex - 1
        self.phases.append({"start": pIndex, "end": None, "type": phaseType})
        # TODO: calculate phase stats?

    def updateMode(self):
        """
        Computes the current flight mode (straight, circling, stopped).

        This means computing the flight mode of the last point in the current
        track. If required, it adds a new phase to the global list.
        """
        # First point, just set as stopped and return
        if len(self.points) == 1:
            self.points[0]["computeL4"]["mode"] = Flight.STOPPED
            return

        p, pI = self.points[-1], len(self.points) - 1
        p["computeL4"]["mode"] = self.points[-2]["computeL4"]["mode"]
        # Move from stopped to straight
        if p["computeL4"]["mode"] == Flight.STOPPED \
            and p["computeL3"]["gSpeed"] > self.control["minSpeed"]:
            p["computeL4"]["mode"] = Flight.STRAIGHT
            self.newPhase(pI, Flight.STRAIGHT)
        # Move from straight to circling (>= minTurnRate kept for more than minCircleTime)
        elif p["computeL4"]["mode"] == Flight.STRAIGHT:
            curTime, j = p["time"], pI-1
            while j > 0 and (p["time"] - self.points[j]["time"]).seconds < self.control["minCircleTime"]:
                if fabs(self.points[j]["computeL3"]["turnRate"]) >= self.control["minCircleRate"]:
                    j -= 1
                else:
                    return
            for g in range(j, pI+1):
                self.points[g]["computeL4"]["mode"] = Flight.CIRCLING
            self.newPhase(pI, Flight.CIRCLING)
        # Move from circling to straight (< minTurnRate for more than minStraightTime)
        elif p["computeL4"]["mode"] == Flight.CIRCLING:
            curTime, j = p["time"], pI-1
            while j > 0 and (curTime - self.points[j]["time"]).seconds < self.control["minStraightTime"]:
                if fabs(self.points[j]["computeL3"]["turnRate"]) < self.control["minCircleRate"]:
                    j -= 1
                else:
                    return
            for g in range(j, pI+1):
                self.points[g]["computeL4"]["mode"] = Flight.STRAIGHT
            self.newPhase(pI, Flight.STRAIGHT)

    def pathInKml(self):
        """
        Returns the flight's track in KML format.
        """
        pathKml = ""
        for point in self.points:
            pathKml += "%.2f,%.2f,%d " % (point["latdg"], point["londg"], point["gAlt"])
        return "<LineString><coordinates>%s</coordinates></LineString>" % pathKml

    def __str__(self):
        return "date=%s :: pilot=%s :: type=%s :: reg=%s" % (self.metadata["dte"],
                self.metadata["plt"], self.metadata["gty"], 
                self.metadata["gid"])

class FlightParser(FlightBase):
    """
    Parses a given flight track in IGC format.

    self.flight: the Flight object
    self.rawFlight: the flight in the given IGC format
    """

    def __init__(self, rawFlight, autoParse=True):
        self.flight = Flight()
        self.flight.rawFlight = rawFlight
        if autoParse:
            self.parse()

    def parse(self):
        """
        Triggers the parse.

        See the link below for details on parsing IGC tracks.
        http://carrier.csi.cam.ac.uk/forsterlewis/soaring/igc_file_format/igc_format_2008.html

        It relies on the parse*() methods to parse each individual record.
        """
        lines = self.flight.rawFlight.split("\n")
        for line in lines:
            if line != "":
                getattr(self, "parse%s" % line[0])(line.strip())

    def parseA(self, record):
        self.flight.metadata["mfr"] = record[1:4]
        self.flight.metadata["mfrId"] = record[4:7]
        self.flight.metadata["mfrIdExt"] = record[7:]

    def parseB(self, record):
        self.flight.putPoint(datetime.strptime(record[1:7], "%H%M%S"), record[7:15], record[15:24],
                record[24], int(record[25:30]), int(record[30:35]))

    def parseC(self, record):
        None

    def parseF(self, record):
        None

    def parseG(self, record):
        None

    def parseH(self, record):
        hType = record[2:5].lower()
        if hType == 'dte':
            self.flight.metadata['dte'] = datetime.strptime(record[5:], "%d%m%y")
        elif hType == 'fxa':
            self.flight.metadata[hType] = record[5:]
        else:
            self.flight.metadata[hType] = record[record.find(':')+1:]

    def parseI(self, record):
        None

    def parseJ(self, record):
        None

    def parseK(self, record):
        None

    def parseL(self, record):
        None

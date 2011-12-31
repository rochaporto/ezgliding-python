import flight

from math import sin, cos, asin, acos, atan2, fabs, sqrt, radians, degrees, pi
from optparse import OptionParser

class Optimizer(flight.FlightBase):
    """
    Evaluates the flight distance following different rules and algorithms.
    
    For each different rule the corresponding circuit is returned.

    Rules currently include:
      1 turnpoint (out and return)
      2 turnpoints
      3 turnpoints

    It would be good to add in the future:
      4 turnpoints (online contest style)
      FAI triangle
    """

    def __init__(self, flight):
        """
        Initiates the optimizer objects.
        """
        self.flight = flight
        self.maxCPDistance = 0 # Maximum distance between 2 consecutive points
        self.prepare()

    def prepare(self):
        """
        Calculates and stores the maximum distance between any two points.

        This is useful for optimization purposes (see forward()).
        """
        for i in range(0, len(self.flight.points)-1):
            distance = self.distance(self.flight.points[i], self.flight.points[i+1])
            if distance > self.maxCPDistance:
                self.maxCPDistance = distance

    def forward(self, i, distance):
        """
        Evaluates if we can jump points, and returns the next point.

        Knowing the max distance between any 2 points, then we know how many 
        points forward (at least) we need to achieve that distance.
        """
        step = int(distance / self.maxCPDistance)
        if step > 0:
            return i + step
        return i+1

    def optimize1(self):
        """
        Optimizes the track for 1 turnpoint (out and return).

        Returns the circuit:
          {"sta": ..., "tps": [..], "end": ..., "distance": ...}
        """
        circuit = {"sta": None, "tps": None, "end": None, "distance": 0.0}
        flight, nPoints = self.flight, len(self.flight.points)
        sta, tp1, end = 0, 1, nPoints-1
        while tp1 < nPoints-1:
            distance = self.distance(flight.points[sta], flight.points[tp1]) \
                + self.distance(flight.points[tp1], flight.points[end])
            if distance > circuit["distance"]:
                circuit = {"sta": sta, "tps": [tp1], "end": end, "distance": distance}
                tp1 += 1
                print circuit
            else:
                tp1 = self.forward(tp1, 0.5 * (circuit["distance"] - distance))
        return circuit

    def optimize2(self):
        """
        Optimizes the track for 2 turnpoints.

        Returns the circuit:
          {"sta": ..., "tps": [..], "end": ..., "distance": ...}
        """
        circuit = {"sta": None, "tps": None, "end": None, "distance": 0.0}
        flight, nPoints = self.flight, len(self.flight.points)
        sta, tp1, tp2, end = 0, 1, -1, nPoints-1
        for tp1 in range(1, nPoints-2):
            leg1 = self.distance(flight.points[sta], flight.points[tp1])
            tp2 = tp1+1
            while tp2 < nPoints-1:
                distance = leg1 + self.distance(flight.points[tp1], flight.points[tp2]) \
                    + self.distance(flight.points[tp2], flight.points[end])
                if distance > circuit["distance"]:
                    circuit = {"sta": sta, "tps": [tp1, tp2], "end": end, "distance": distance}
                    tp2 += 1
                    print circuit
                else:
                    tp2 = self.forward(tp2, 0.5 * (circuit["distance"] - distance))
        return circuit

    def optimize3(self):
        """
        Optimizes the track for 3 turnpoints (netcoupe style).

        Returns the circuit:
          {"sta": ..., "tps": [..], "end": ..., "distance": ...}
        """
        circuit = {"sta": None, "tps": None, "end": None, "distance": 0.0}
        flight, nPoints = self.flight, len(self.flight.points)
        sta, tp1, tp2, tp3, end = 0, -1, -1, -1, nPoints-1
        for tp1 in range(1, nPoints-3):
            leg1 = self.distance(flight.points[sta], flight.points[tp1])
            for tp2 in range(tp1+1, nPoints-2):
                leg2 = self.distance(flight.points[tp1], flight.points[tp2])
                tp3 = tp2+1
                while tp3 < nPoints-1:
                    leg3 = self.distance(flight.points[tp2], flight.points[tp3])
                    distance = leg1 + leg2 + leg3 + self.distance(flight.points[tp3], flight.points[end])
                    if distance > circuit["distance"]:
                        circuit = {"sta": sta, "tps": [tp1, tp2, tp3], "end": end, "distance": distance}
                        print circuit
                        tp3 += 1
                    else:
                        tp3 = self.forward(tp3, 0.5 *(circuit["distance"] - distance))
        return circuit


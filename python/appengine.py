import logging

from google.appengine.api import taskqueue, urlfetch
from google.appengine.ext.webapp import RequestHandler, WSGIApplication
from google.appengine.ext.webapp.util import run_wsgi_app

import crawler

class FlightCrawler(RequestHandler):
    """
    Reusable RequestHandler capable of fetching flights from different
    online competitions.

    Usually used as a cron job, with many instances with different configs.

    Flights are first fetched and then pushed to the competition queue.
    """
    def get(self):
        """
        This is the method called by the appengine Handler.
        """
        flights = None

        crawlType = self.request.get("type")
        logging.info("Crawling flights for %s" % crawlType)
        if crawlType == "netcoupe":
            crawl = crawler.NetcoupeCrawler()
            flights = crawl.crawl(crawl.lastProcessedId())
        else:
            self.error(500)
        self.queue(flights, crawlType=crawlType)


    def getTask(self, flightId, crawlType, url):
        """
        Returns a Task object with all the given data in the expected places,
        ready to be added to its queue.
        """
        task = taskqueue.Task(
                url="/crawler/worker", 
                params={"id": flightId, "type": crawlType, "url": url})
        return task

    def queue(self, flights, crawlType="netcoupe"):
        """
        Queues the given flights for later processing.
        """
        for flight in flights:
            task = self.getTask(flight[0], crawlType, flight[1])
            task.add("crawler-%s" % crawlType)
            logging.info("Queued flight %d for processing" % flight[0])

class FlightWorker(RequestHandler):
    """
    Handler to process flights (parse, analyse) and store them.

    Normally used as a task queue processor.
    """
    def post(self):
        """
        The RequestHandler method called by the task processing.
        """
        flightId = self.request.get("id")
        logging.info("processing flight :: %s" % flightId)
        #exporter = FlightExporter(reader.flight)
        #req = urllib2.Request(self.fusionTablesUri,
        #        urllib.urlencode({"sql": exporter.toFusionTable(872803)}),
        #        {"Authorization": "GoogleLogin auth=%s" % self.authToken,
        #        "Content-Type": "application/x-www-form-urlencoded"})
        #resp = urllib2.urlopen(req)

def main():
    """
    The main method required by appengine.

    Associates url paths with each Handler.
    """
    app = WSGIApplication([
            ('/crawler', FlightCrawler),
            ('/crawler/worker', FlightWorker),
            ], debug=True)
    logging.getLogger().setLevel(logging.DEBUG)
    run_wsgi_app(app)

if __name__ == '__main__':
    main()

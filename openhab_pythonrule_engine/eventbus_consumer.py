import logging
import time
import requests
import json
import sseclient
from threading import Thread



class EventConsumer:

    def __init__(self, openhab_uri: str, event_listener):
        if not openhab_uri.endswith("/"):
            openhab_uri = openhab_uri + "/"
        self.event_uri =  openhab_uri + "rest/events"
        self.event_listener = event_listener
        self.is_running = True
        self.thread = None

    def start(self):
        self.thread = Thread(target=self.__listen)
        self.thread.start()

    def __listen(self):
        while self.is_running:
            try:
                logging.debug("opening sse stream (" + self.event_uri + ")")
                response = requests.get(self.event_uri, stream=True)
                client = sseclient.SSEClient(response)

                try:
                    for event in client.events():
                        data = json.loads(event.data)
                        self.event_listener.on_event(data)
                finally:
                    logging.debug("closing sse stream")
                    client.close()
                    response.close()
            except Exception as e:
                logging.error("error occurred consuming sse of " + self.event_uri, e)
                time.sleep(5)

    def stop(self):
        self.is_running = False
        Thread.join(self.thread)


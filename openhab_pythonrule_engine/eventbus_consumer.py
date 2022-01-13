import logging
import time
import requests
import json
import sseclient
from threading import Thread
from typing import Optional
from dataclasses import dataclass


logging = logging.getLogger(__name__)




@dataclass()
class ItemEvent:
    item_name: str
    operation: str
    payload: str


def parse_item_event(event) -> Optional[ItemEvent]:
    topic = event.get("topic", "")
    if topic.startswith('openhab') or topic.startswith('smarthome'):
        try:
            parts = topic.split("/")
            if parts[1] == 'items':
                item_name = parts[2]
                operation = parts[3]
                return ItemEvent(item_name, operation, event.get("payload", ""))
        except Exception as e:
            logging.warning("Error occurred by handling event " + str(event), e)
    return None


class EventConsumer:

    def __init__(self, openhab_uri: str, event_listener):
        if not openhab_uri.endswith("/"):
            openhab_uri = openhab_uri + "/"
        self.event_uri =  openhab_uri + "rest/events"
        self.event_listener = event_listener
        self.is_running = True
        self.thread = None

    def start(self):
        self.thread = Thread(target=self.__listen, daemon=True)
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


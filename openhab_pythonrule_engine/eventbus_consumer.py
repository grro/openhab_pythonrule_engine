import logging
import time
import requests
import json
import sseclient
from datetime import datetime
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
        logging.info("opening sse stream " + self.event_uri)
        self.thread = Thread(target=self.__listen, daemon=True)
        self.thread.start()

    def __listen(self):
        previous_error_time = None
        while self.is_running:
            try:
                conn_timeout = 30
                read_timeout = 5 * 60
                response = requests.get(self.event_uri, stream=True, timeout=(conn_timeout, read_timeout))
                client = sseclient.SSEClient(response)
                if previous_error_time is None:
                    logging.info("sse stream " + self.event_uri + " established")
                else:
                    logging.info("sse stream " + self.event_uri + " re-opened (after " + str(round((datetime.now() - previous_error_time).total_seconds()/60)) + " min)")
                previous_error_time = None
                try:
                    for event in client.events():
                        if self.is_running:
                            data = json.loads(event.data)
                            self.event_listener.on_event(data)
                        else:
                            break
                finally:
                    logging.debug("closing sse stream")
                    client.close()
                    response.close()
            except Exception as e:
                retry_in_sec = 5
                if previous_error_time is None:
                    logging.warning("sse stream " + self.event_uri + " failed: " + str(e))
                    logging.info("try to reconnect sse stream in (each) " + str(retry_in_sec) + " sec")
                    previous_error_time = datetime.now()
                time.sleep(retry_in_sec)

    def stop(self):
        self.is_running = False


import logging
from logging import INFO
from dateutil import parser
from datetime import datetime
from dataclasses import dataclass
from requests import Session
from threading import RLock
from requests.auth import HTTPBasicAuth
from typing import Optional, List, Dict, Any
from openhab_pythonrule_engine.cache import Cache

logging = logging.getLogger(__name__)


@dataclass
class Item:
    item_name: str
    read_only: bool
    group_names: List[str]
    value: Any

    def serialize(self, value) -> Optional[str]:
        pass

    def get_state(self):
        pass

    def get_state_as_text(self) -> str:
        pass

    def get_state_as_boolean(self) -> bool:
        pass

    def get_state_as_numeric(self) -> float:
        pass

    def get_state_as_datetime(self) -> datetime:
        text = self.get_state_as_text()
        return datetime.fromtimestamp(parser.parse(text).timestamp())


@dataclass
class TextItem(Item):
    value: str

    def get_state(self):
        return self.get_state_as_text()

    def get_state_as_text(self) -> str:
        return self.value

    def get_state_as_boolean(self) -> bool:
        if self.value is None:
            return False
        else:
            return True if (self.get_state_as_text() .lower() in ["true", "on"]) else False

    def get_state_as_numeric(self) -> float:
        if self.value is None:
            return -1
        else:
            return float(self.value)

    def serialize(self, value_to_serialize) -> Optional[str]:
        if value_to_serialize is None:
            return None
        elif type(value_to_serialize) == bool:
            return "ON" if value_to_serialize else "OFF"
        elif type(value_to_serialize) == datetime:
            return value_to_serialize.strftime('%Y-%m-%dT%H:%M:%S')
        elif type(value_to_serialize) == int:
            return str(int(value_to_serialize))
        elif type(value_to_serialize) == float:
            return str(float(value_to_serialize))
        else:
            return str(value_to_serialize)


@dataclass
class NumericItem(Item):
    item_name: str
    read_only: bool
    value: float

    def get_state(self):
        return self.get_state_as_numeric()

    def get_state_as_numeric(self) -> float:
        return self.value

    def get_state_as_boolean(self) -> bool:
        if self.value is None:
            return False
        else:
            return self.value != 0

    def get_state_as_text(self) -> str:
        if self.value is None:
            return ""
        return str(self.value)

    def serialize(self, value_to_serialize) -> Optional[str]:
        if value_to_serialize is None:
            return None
        else:
            if type(value_to_serialize) == bool:
                return "1" if value_to_serialize else "0"
            elif type(value_to_serialize) == int:
                return str(float(value_to_serialize))
            else:
                return str(value_to_serialize)


@dataclass
class BooleanItem(Item):
    item_name: str
    read_only: bool
    value: bool

    def get_state(self):
        return self.get_state_as_boolean()

    def get_state_as_boolean(self) -> bool:
        if self.value is None:
            return False
        else:
            return self.value

    def get_state_as_numeric(self) -> float:
        if self.value is None:
            return 0
        else:
            return 1 if self.value else 0

    def get_state_as_text(self) -> str:
        if self.value is None:
            return str(False)
        else:
            return str(self.value)

    def serialize(self, value_to_serialize) -> Optional[str]:
        if type(value_to_serialize) == bool:
            return "ON" if value_to_serialize else "OFF"
        elif type(value_to_serialize) == float:
            return "ON" if value_to_serialize == 1.0 else "OFF"
        elif type(value_to_serialize) == int:
            return "ON" if value_to_serialize == 1 else "OFF"
        else:
            return "ON" if (str(value_to_serialize).lower() in ["true", "on"]) else "OFF"


def to_item(data) -> Optional[Item]:
    try:
        if 'stateDescription' in data.keys():
            read_only = data['stateDescription']['readOnly']
        else:
            read_only = False
        if 'groupNames' in data.keys():
            group_names = data['groupNames']
        else:
            group_names = []
        state = data['state']
        if data['type'] == 'Number':
            item = NumericItem(data['name'], read_only, group_names, None if (state == 'NULL' or state == 'UNDEF') else float(state))
        elif data['type'] == 'Switch':
            item = BooleanItem(data['name'], read_only, group_names, None if state == 'NULL' else state == 'ON')
        else:
            item = TextItem(data['name'], read_only, group_names, None if (state == 'NULL' or state == 'UNDEF') else state)
        return item
    except Exception as e:
        logging.warning("error occurred mapping " + str(data) + " to item " + str(e))
        return None


class ItemRegistry:

    def __init__(self, openhab_uri: str, user: str, pwd: str):
        self.__last_updates = []
        self.__last_failed_updates = []
        self.cache = Cache()
        self.credentials = HTTPBasicAuth(user, pwd)
        self.__session = Session()
        self.__lock = RLock()
        if openhab_uri.endswith("/"):
            self.openhab_uri = openhab_uri
        else:
            self.openhab_uri = openhab_uri + "/"

    def __renew_session(self):
        self.__session = Session()

    @property
    def last_updates(self) -> List[str]:
        return self.__last_updates

    @property
    def last_update(self) -> Optional[str]:
        if len(self.last_updates) > 0:
            return self.last_updates[-1]
        else:
            return None

    @property
    def last_failed_updates(self) -> List[str]:
        return self.__last_failed_updates

    @property
    def last_failed_update(self) -> Optional[str]:
        if len(self.last_failed_updates) > 0:
            return self.last_failed_updates[-1]
        else:
            return None

    def on_event(self, event):
        if event.get("type", "") == "ThingUpdatedEvent":
            logging.debug("config change. reset cache")
            self.cache.clear()

    def get_items(self, use_cache: bool = False) -> Dict[str, Item]:
        items = self.cache.read_entry("items", 24 * 60 * 60)
        if items is not None:
            return items
        else:
            with self.__lock:
                uri = self.openhab_uri+ "rest/items"
                try:
                    response = self.__session.get(uri, headers={"Accept": "application/json"}, auth = self.credentials)
                    if response.status_code == 200:
                        items = {}
                        for entry in response.json():
                            item = to_item(entry)
                            if item is not None:
                                items[item.item_name] = item
                        self.cache.add_enry("items", items)
                        return items
                    elif response.status_code == 404:
                        raise Exception("item " +   uri + " not exists " + response.text)
                    else:
                        raise Exception("could not read item state " + uri + " got error " + response.text)
                except Exception as e:
                    self.__renew_session()
                    logging.warning("error occurred by calling " + uri + " " + str(e))

    def get_item(self, item_name: str) -> Optional[Item]:
        with self.__lock:
            uri = self.openhab_uri+ "rest/items/" + item_name
            try:
                response = self.__session.get(uri, headers={"Accept": "application/json"}, auth = self.credentials)
                if response.status_code == 200:
                    data = response.json()
                    return to_item(data)
                elif response.status_code == 404:
                    raise Exception("item " +   uri + " not exists " + response.text)
                elif response.status_code == 401:
                    raise Exception("auth error. user=" + self.credentials.username)
                else:
                    raise Exception("could not read item state " + uri + " got error " + response.text)
            except Exception as e:
                self.__renew_session()
                logging.warning("error occurred by calling " + uri + " " + str(e))

    def has_item(self, item_name: str) -> bool:
        if item_name is None:
            return False
        else:
            return self.get_item(item_name) != None

    def get_group_membernames(self, group_name) -> List[str]:
        return [item.item_name for item in self.get_items().values() if group_name in item.group_names]

    def __on_last_update(self, item_name: str, value):
        self.__last_updates.append("[" + datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + "] new value " + item_name + ": " + str(value))
        while len(self.__last_updates) > 20:
            self.__last_updates.pop(0)

    def __on_last_failed_update(self, item_name: str, value, error_message: str):
        self.__last_failed_updates.append("[" + datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + "] error occured by setting " + item_name + " with " + str(value) + "  " + error_message)
        while len(self.__last_failed_updates) > 20:
            self.__last_failed_updates.pop(0)

    def set_item_state(self, item_name: str, value: str):
        with self.__lock:
            uri = self.openhab_uri+ "rest/items/" + item_name
            try:
                response = self.__session.post(uri, data=value, headers={"Content-type": "text/plain"}, auth = self.credentials)
                if response.status_code == 200:
                    self.__on_last_update(item_name, value)
                    return
                elif response.status_code == 404:
                    txt = "item " +   uri + " not exists " + response.text
                    self.__on_last_failed_update(item_name, value, txt)
                    raise Exception(txt)
                elif response.status_code == 401:
                    txt = "auth error. user=" + self.credentials.username
                    self.__on_last_failed_update(item_name, value, txt)
                    raise Exception(txt)
                else:
                    txt = "could not update item state " + uri + " got error " + response.text
                    self.__on_last_failed_update(item_name, value, txt)
                    raise Exception(txt)
            except Exception as e:
                self.__renew_session()
                logging.warning("error occurred by performing put on " + uri + " " + str(e))

    def get_item_metadata(self, item_name: str) -> Optional[Item]:
        items_meta_data = self.get_items(use_cache=True)
        for name in items_meta_data.keys():
            if item_name == name:
                return items_meta_data[item_name]
        return None

    def __get_item_metadata_or_throw_error(self, item_name: str) -> Item:
        item_metadata = self.get_item_metadata(item_name)
        if item_metadata is None:
            raise Exception("item " + item_name + " not exists")
        else:
            return item_metadata

    def get_state(self, item_name: str, dflt):
        state = self.get_item(item_name)
        if state is None or state.value is None:
            return dflt
        else:
            return state.get_state()

    def get_state_as_numeric(self, item_name: str, dflt: float=-1) -> float:
        state = self.get_item(item_name)
        if state is None or state.value is None:
            return dflt
        else:
            return state.get_state_as_numeric()

    def get_state_as_int(self, item_name: str, dflt: float=-1) -> int:
        return int(self.get_state_as_numeric(item_name, dflt))

    def get_state_as_boolean(self, item_name: str, dflt: bool=False) -> bool:
        state = self.get_item(item_name)
        if state is None or state.value is None:
            return dflt
        else:
            return state.get_state_as_boolean()

    def get_state_as_text(self, item_name: str, dflt: str="") -> str:
        state = self.get_item(item_name)
        if state is None or state.value is None:
            return dflt
        else:
            return state.get_state_as_text()

    def get_state_as_datetime(self, item_name: str, datetime_string: str="1970-01-01") -> datetime:
        state = self.get_item(item_name)
        if state is None or state.value is None:
            return parser.parse(datetime_string)
        else:
            return state.get_state_as_datetime()

    def is_equals(self, state1: str, state2: str):
        return state1 == state2

    def __state_not_equals(self, item_name: str, new_state) -> bool:
        try:
            old_state = self.get_state(item_name, None)
            item_metadata = self.__get_item_metadata_or_throw_error(item_name)
            return item_metadata.serialize(old_state) != item_metadata.serialize(new_state)
        except Exception as e:
            logging.warning("error occurred fetching state of " + item_name + " " + str(e))
            return True

    def set_state(self, item_name: str, new_state, reason: str = "", log_level: int = INFO, force: bool = False) -> bool:
        if new_state is None:
            logging.warning("try to set " + item_name + " = None. ignoring it")
        else:
            if force or self.__state_not_equals(item_name, new_state):
                try:
                    serialized_new_state = self.__get_item_metadata_or_throw_error(item_name).serialize(new_state)
                    try:
                        self.set_item_state(item_name, serialized_new_state)
                        logging.log(log_level, "set " + item_name + " = " + serialized_new_state + " " + reason)
                        return True
                    except Exception as e:
                        logging.warning("could not set " + item_name + " = " + str(serialized_new_state) + " " + str(e))
                except Exception as e:
                    logging.warning("could not serialized value " + str(new_state) + " to update " + item_name + " " + str(e))
        return False

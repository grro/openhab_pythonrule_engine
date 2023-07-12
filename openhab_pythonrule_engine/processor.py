import logging
from abc import ABC
from openhab_pythonrule_engine.trigger import Trigger
from openhab_pythonrule_engine.item_registry import ItemRegistry

logging = logging.getLogger(__name__)


class Processor(ABC):

    def __init__(self, name: str, item_registry: ItemRegistry, listener):
        self.name = name
        self.item_registry = item_registry
        self.is_running = False
        self.triggers = set()
        self.listener = listener

    def __notify_listener(self, trigger: Trigger, error: Exception = None):
        try:
            self.listener(trigger, error)
        except Exception as e:
            logging.warning("error occurred calling " + self.listener + " " + str(e))

    def add_trigger(self, trigger: Trigger):
        logging.info(" * register " + trigger.module + "#" + trigger.function_name + "(...) - trigger '" + trigger.expression + "'")
        self.triggers.add(trigger)
        self.on_add_trigger(trigger)

    def remove_triggers(self, module: str):
        trigger_of_module = {trigger for trigger in self.triggers if trigger.module == module}
        logging.info(" * unregister " + module + " (" + self.name + ")")
        self.triggers = self.triggers - trigger_of_module
        self.on_remove_triggers(module)

    def invoke_trigger(self, trigger: Trigger):
        try:
            trigger.invoke(self.item_registry)
            self.__notify_listener(trigger)
        except Exception as e:
            logging.warning("Error occurred by executing rule " + trigger.function_name, e)
            self.__notify_listener(trigger, e)

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.on_start()
            logging.info("'" + self.name + " processor' started")

    def on_start(self):
        pass

    def stop(self):
        self.is_running = False
        self.on_stop()
        logging.info("'" + self.name + "' processor stopped")

    def on_stop(self):
        pass

    def on_add_trigger(self, trigger: Trigger):
        pass

    def on_remove_triggers(self, module: str):
        pass


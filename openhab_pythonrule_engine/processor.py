import logging
from abc import ABC
from typing import Set
from openhab_pythonrule_engine.trigger import Trigger
from openhab_pythonrule_engine.item_registry import ItemRegistry


class Processor(ABC):

    def __init__(self, name: str, item_registry: ItemRegistry):
        self.name = name
        self.item_registry = item_registry
        self.is_running = False
        self.trigger_by_module = {}

    @property
    def triggers(self) -> Set[Trigger]:
        return set().union(*self.trigger_by_module.values())

    def add_trigger(self, trigger: Trigger):
        logging.info(" * " + trigger.name + "(...): trigger '" + trigger.expression + "' has been registered")
        triggers = self.trigger_by_module.get(trigger.module, set())
        triggers.add(trigger)
        self.trigger_by_module[trigger.module] = triggers
        self.on_add_trigger(trigger)

    def remove_triggers(self, module: str):
        if module in self.trigger_by_module.keys():
            logging.info("removing all " + str(len(self.trigger_by_module[module])) + self.name + " trigger of '" + module + "'")
            del self.trigger_by_module[module]
        self.on_remove_triggers(module)

    def process_trigger(self, trigger: Trigger):
        try:
            trigger.invoke(self.item_registry)
        except Exception as e:
            logging.warning("Error occurred by executing rule " + trigger.name, e)

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


import logging
from abc import ABC
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from openhab_pythonrule_engine.invoke import Invoker
from openhab_pythonrule_engine.item_registry import ItemRegistry


@dataclass
class Execution:
    datetime: datetime
    error: Optional[Exception] = None

    def __str__(self):
        text = self.datetime.strftime("%Y-%m-%d-T%H:%M:%S")
        if self.error is not None:
            text += "  (Error: " + str(self.error) + ")"
        return text

    def __repr__(self):
        return self.__str__()


class Trigger(ABC):

    def __init__(self, expression: str, func):
        self.expression = expression
        self.func = func
        self.invoker = Invoker.create(func)
        self.last_executions = []
        self.last_errors = {}

    def is_valid(self):
        return self.invoker is not None

    def invoke(self, item_registry: ItemRegistry):
        execution = None
        if len(self.last_executions) > 20:
            self.last_executions.pop(0)
        try:
            self.invoker.invoke(item_registry)
            self.last_executions.append(Execution(datetime.now(), None))
        except Exception as e:
            self.last_executions.append(Execution(datetime.now(), e))
            logging.warning("Error occurred by invoking " + self.name, e)



    @property
    def module(self):
        return self.func.__module__

    @property
    def name(self):
        return self.func.__name__

    def __str__(self):
        return self.expression


class CronTrigger(Trigger):

    def __init__(self, cron: str, expression: str, func):
        self.cron = cron
        super().__init__(expression, func)


class SystemEventTrigger(Trigger):

    def __init__(self, expression: str, func):
        super().__init__(expression, func)


class ItemChangedTrigger(Trigger):

    def __init__(self, item_name: str, operation: str, expression: str, func):
        self.item_name = item_name
        self.operation = operation
        super().__init__(expression, func)

    def on_event(self, event):
        topic = event.get("topic", "")
        if topic.startswith('openhab') or topic.startswith('smarthome'):
            try:
                parts = topic.split("/")
                #print(parts)
                if parts[1] == 'items':
                    item_name = parts[2]
                    if item_name == self.item_name:
                        operation = parts[3]
                        if operation == 'statechanged':
                            logging.debug("executing rule " + self.invoker.name + " (trigger 'Item " + item_name + " changed')")
                            self.invoke(ItemRegistry.instance())
            except Exception as e:
                logging.warning("Error occurred by handling event " + str(event), e)



class TriggerRegistry:

    def __init__(self):
        self.triggers_by_module = {}

    def register(self, trigger: Trigger):
        triggers = self.triggers_by_module.get(trigger.module, set())
        triggers.add(trigger)
        self.triggers_by_module[trigger.module] = triggers

    def deregister(self, module):
        if module in list(self.triggers_by_module.keys()):
            logging.info("removing all " + str(len(self.triggers_by_module[module])) + " triggers of '" + module + "'")
            del self.triggers_by_module[module]

    def get_triggers_by_type(self, type):
        filterred_triggers = []
        for triggers in self.triggers_by_module.values():
            for trigger in triggers:
                if isinstance(trigger, type):
                    filterred_triggers.append(trigger)
        return filterred_triggers


import json
import logging
from abc import ABC
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from openhab_pythonrule_engine.invoke import Invoker
from openhab_pythonrule_engine.item_registry import ItemRegistry
from openhab_pythonrule_engine.eventbus_consumer import ItemEvent



logging = logging.getLogger(__name__)



class Trigger(ABC):

    def __init__(self, expression: str, func):
        self.expression = expression
        self.func = func
        self.invoker = Invoker.create(func)
        self.last_executions = []
        self.last_errors = {}
        self.listeners = set()

    def add_listener(self, listener):
        self.listeners.add(listener)

    def is_valid(self) -> bool:
        return self.invoker is not None

    def invoke(self, item_registry: ItemRegistry):
        logging.debug("executing rule " + self.invoker.name + " (triggerred by '" + self.expression + "')")
        if len(self.last_executions) > 20:
            self.last_executions.pop(0)
        try:
            self.invoker.invoke(item_registry)
            self.last_executions.append(Execution(self, datetime.now(), None))
        except Exception as e:
            self.last_executions.append(Execution(self, datetime.now(), e))
            logging.warning("Error occurred by invoking " + self.name, e)
        for listener in self.listeners:
            try:
                listener(self)
            except Exception as e:
                logging.warning("error occurred by calling listener", e)

    @property
    def module(self) -> str:
        return self.func.__module__

    @property
    def name(self) -> str:
        return self.func.__name__

    def fingerprint(self) -> str:
        return str(self.func) + "/" + self.expression

    def __hash__(self):
        return hash(self.fingerprint())

    def __eq__(self, other):
        return self.fingerprint() == other.fingerprint()

    def __lt__(self, other):
        return self.fingerprint() < other.fingerprint()

    def __str__(self):
        return self.expression

    def __repr__(self):
        return self.__str__()


class ManualTrigger(Trigger):

    def __init__(self, func):
        super().__init__("manual", func)


class CronTrigger(Trigger):

    def __init__(self, cron: str, expression: str, func):
        self.cron = cron
        super().__init__(expression, func)


class RuleLoadedTrigger(Trigger):

    def __init__(self, expression: str, func):
        super().__init__(expression, func)


class ItemTrigger(Trigger):

    def __init__(self, expression: str, func):
        super().__init__(expression, func)

    def matches(self, item_event: ItemEvent) -> bool:
        return False


class ItemReceivedCommandTrigger(ItemTrigger):

    def __init__(self, item_name: str, command: str, expression: str, func):
        self.item_name = item_name
        self.command = command
        super().__init__(expression, func)

    def matches(self, item_event: ItemEvent) -> bool:
        if item_event.item_name == self.item_name and item_event.operation.lower() == 'command':
            js = json.loads(item_event.payload)
            if js.get('type', '') == 'OnOff':
                op = js.get('value', '')
                return ('command ' + op).lower() == self.command
        return False


class ItemChangedTrigger(ItemTrigger):

    def __init__(self, item_name: str, operation: str, expression: str, func):
        self.item_name = item_name
        self.operation = operation
        super().__init__(expression, func)

    def matches(self, item_event: ItemEvent) -> bool:
        return item_event.item_name == self.item_name and item_event.operation == 'statechanged'




@dataclass
class Execution:
    trigger: Trigger
    datetime: datetime
    error: Optional[Exception] = None

    def __lt__(self, other):
        return self.datetime < other.datetime

    def __eq__(self, other):
        return self.datetime == other.datetime

    def __str__(self):
        text = self.datetime.strftime("%Y-%m-%d-T%H:%M:%S") + " " + str(self.trigger)
        if self.error is not None:
            text += "  (Error: " + str(self.error) + ")"
        return text

    def __repr__(self):
        return self.__str__()


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


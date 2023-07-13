import logging
from abc import ABC, abstractmethod
from datetime import datetime
from openhab_pythonrule_engine.invoke import Invoker
from openhab_pythonrule_engine.item_registry import ItemRegistry

logging = logging.getLogger(__name__)


class Rule(ABC):

    def __init__(self, trigger_expression: str, func):
        self.trigger_expression = trigger_expression
        self.__func = func
        self.__invoker = Invoker.create(func)
        self.last_executed = None
        self.last_failed = None

    def invoke(self, item_registry: ItemRegistry):
        try:
            logging.debug('executing ' + self.module + '.py#' + self.function_name + '(...) on @when("' + self.trigger_expression + '")')
            self.__invoker.invoke(item_registry)
            self.last_executed = datetime.now()
        except Exception as e:
            logging.warning("Error occurred by executing rule " + self.function_name, e)
            self.last_failed = datetime.now()

    @property
    def module(self) -> str:
        return self.__func.__module__

    @property
    def function_name(self) -> str:
        return self.__func.__name__

    def fingerprint(self) -> str:
        return str(self.module) + "/" + str(self.function_name) + "/" + self.trigger_expression

    def __hash__(self):
        return hash(self.fingerprint())

    def __eq__(self, other):
        return self.fingerprint() == other.fingerprint()

    def __lt__(self, other):
        return self.fingerprint() < other.fingerprint()



class ExecutionListener(ABC):

    @abstractmethod
    def on_executed(self, rule: Rule, error: Exception):
        pass

import logging
from abc import ABC
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from openhab_pythonrule_engine.invoke import Invoker
from openhab_pythonrule_engine.item_registry import ItemRegistry




class Trigger(ABC):

    def __init__(self, expression: str, func):
        self.expression = expression
        self.func = func
        self.invoker = Invoker.create(func)

    def is_valid(self) -> bool:
        return self.invoker is not None

    def invoke(self, item_registry: ItemRegistry):
        logging.debug("executing rule " + self.invoker.name + " (triggerred by '" + self.expression + "')")
        try:
            self.invoker.invoke(item_registry)
        except Exception as e:
            logging.warning("Error occurred by invoking " + self.name, e)

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




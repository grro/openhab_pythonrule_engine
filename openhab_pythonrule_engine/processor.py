import logging
import weakref
from abc import ABC
from openhab_pythonrule_engine.rule import Rule
from openhab_pythonrule_engine.item_registry import ItemRegistry

logging = logging.getLogger(__name__)


class Processor(ABC):

    def __init__(self, name: str, item_registry: ItemRegistry, execution_listener_ref: weakref):
        self.name = name
        self.item_registry = item_registry
        self.is_running = False
        self.rules = set()
        self.execution_listener_ref = execution_listener_ref

    def __notify_listener(self, rule: Rule, error: Exception = None):
        try:
            execution_listener = self.execution_listener_ref()
            if execution_listener is not None:
                execution_listener.on_executed(rule, error)
        except Exception as e:
            logging.warning("error occurred calling " + self.execution_listener_ref() + " " + str(e))

    def add_rule(self, rule: Rule):
        logging.info(' * register ' + rule.module + '.py#' + rule.function_name + '(...) on @when("' + rule.trigger_expression + '")')
        self.rules.add(rule)
        self.on_add_rule(rule)

    def remove_rules(self, module: str):
        rules_of_module = {rule for rule in self.rules if rule.module == module}
        for rule in rules_of_module:
            logging.info(' * unregister ' + rule.module + '.py#' + rule.function_name + '(...) on @when("' + rule.trigger_expression + '")')
        self.rules = self.rules - rules_of_module
        self.on_remove_rules(module)

    def invoke_rule(self, rule: Rule):
        try:
            rule.invoke(self.item_registry)
            self.__notify_listener(rule)
        except Exception as e:
            logging.warning("Error occurred by executing rule " + rule.function_name, e)
            self.__notify_listener(rule, e)

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

    def on_add_rule(self, rule: Rule):
        pass

    def on_remove_rules(self, module: str):
        pass


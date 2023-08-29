import weakref
from openhab_pythonrule_engine.invoke import InvokerManager
from openhab_pythonrule_engine.rule import Rule
from openhab_pythonrule_engine.processor import Processor
from openhab_pythonrule_engine.item_registry import ItemRegistry



class RuleLoadedRule(Rule):

    def __init__(self, trigger_expression: str, func, invoker_manager: InvokerManager):
        super().__init__(trigger_expression, func, invoker_manager)


class RuleLoadedProcessor(Processor):

    def __init__(self, item_registry: ItemRegistry, execution_listener_ref: weakref, invoker_manager: InvokerManager):
        self.invoker_manager = invoker_manager
        super().__init__("rule loaded", item_registry, execution_listener_ref)

    def on_annotation(self, annotation: str, func):
        if annotation.lower().strip() == "rule loaded":
            self.add_rule(RuleLoadedRule(annotation, func, self.invoker_manager))
            return True
        return False

    def on_add_rule(self, rule: Rule):
        self.invoke_rule(rule)

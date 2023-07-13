import weakref
from openhab_pythonrule_engine.rule import Rule
from openhab_pythonrule_engine.processor import Processor
from openhab_pythonrule_engine.item_registry import ItemRegistry



class RuleLoadedRule(Rule):

    def __init__(self, trigger_expression: str, func):
        super().__init__(trigger_expression, func)


class RuleLoadedProcessor(Processor):

    def __init__(self, item_registry: ItemRegistry, execution_listener_ref: weakref):
        super().__init__("rule loaded", item_registry, execution_listener_ref)

    def parser(self):
        return RuleLoadedTriggerParser(self).on_annotation

    def on_add_rule(self, rule: Rule):
        self.invoke_rule(rule)


class RuleLoadedTriggerParser:

    def __init__(self, rule_loaded_processor: RuleLoadedProcessor):
        self.rule_loaded_processor = rule_loaded_processor

    def on_annotation(self, annotation: str, func):
        if annotation.lower().strip() == "rule loaded":
            self.rule_loaded_processor.add_rule(RuleLoadedRule(annotation, func))
            return True
        return False

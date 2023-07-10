from openhab_pythonrule_engine.trigger import Trigger
from openhab_pythonrule_engine.processor import Processor
from openhab_pythonrule_engine.item_registry import ItemRegistry


class RuleLoadedTrigger(Trigger):

    def __init__(self, expression: str, func):
        super().__init__(expression, func)


class RuleLoadedProcessor(Processor):

    def __init__(self, item_registry: ItemRegistry, listener):
        super().__init__("rule loadded", item_registry, listener)

    def parser(self):
        return RuleLoadedTriggerParser(self).on_annotation

    def on_add_trigger(self, trigger: Trigger):
        self.process_trigger(trigger)


class RuleLoadedTriggerParser:

    def __init__(self, rule_loaded_processor: RuleLoadedProcessor):
        self.rule_loaded_processor = rule_loaded_processor

    def on_annotation(self, annotation: str, func):
        if annotation.lower().strip() == "rule loaded":
            self.rule_loaded_processor.add_trigger(RuleLoadedTrigger(annotation, func))
            return True
        return False

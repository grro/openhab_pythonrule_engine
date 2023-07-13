import json
import logging
import weakref
from openhab_pythonrule_engine.item_registry import ItemRegistry
from openhab_pythonrule_engine.rule import Rule
from openhab_pythonrule_engine.processor import Processor
from openhab_pythonrule_engine.eventbus_consumer import EventConsumer, ItemEvent, parse_item_event

logging = logging.getLogger(__name__)


class ItemRule(Rule):

    def __init__(self, trigger_expression: str, func):
        super().__init__(trigger_expression, func)

    def matches(self, item_event: ItemEvent) -> bool:
        return False


class ItemReceivedCommandRule(ItemRule):

    def __init__(self, item_name: str, command: str, trigger_expression: str, func):
        self.item_name = item_name
        self.command = command
        super().__init__(trigger_expression, func)

    def matches(self, item_event: ItemEvent) -> bool:
        if item_event.item_name == self.item_name and item_event.operation.lower() == 'command':
            js = json.loads(item_event.payload)
            if js.get('type', '') == 'OnOff':
                op = js.get('value', '')
                return ('command ' + op).lower() == self.command
        return False


class ItemChangedRule(ItemRule):

    def __init__(self, item_name: str, operation: str, trigger_expression: str, func):
        self.item_name = item_name
        self.operation = operation
        super().__init__(trigger_expression, func)

    def matches(self, item_event: ItemEvent) -> bool:
        return item_event.item_name == self.item_name and item_event.operation == 'statechanged'


class ItemChangeProcessor(Processor):

    def __init__(self, openhab_uri: str, item_registry: ItemRegistry, execution_listener_ref: weakref):
        self.__event_consumer = EventConsumer(openhab_uri, self)
        super().__init__("item change", item_registry, execution_listener_ref)

    def parser(self):
        return ItemTriggerParser(self).on_annotation

    def on_event(self, event):
        self.item_registry.on_event(event)
        item_event = parse_item_event(event)
        if item_event is not None:
            for item_changed_rule in [rule for rule in self.rules if rule.matches(item_event)]:
                self.invoke_rule(item_changed_rule)

    def on_start(self):
        self.__event_consumer.start()

    def on_stop(self):
        self.__event_consumer.stop()


class ItemTriggerParser:

    def __init__(self, item_change_processor: ItemChangeProcessor):
        self.item_change_processor = item_change_processor

    def on_annotation(self, annotation: str, func) -> bool:
        if annotation.lower().startswith("item") and (annotation.lower().endswith(" received command on") or annotation.lower().endswith(" received command off")):
            itemname_operation_pair = annotation[len("item"):].strip()
            itemname = itemname_operation_pair[:itemname_operation_pair.index(" ")].strip()
            if self.item_change_processor.item_registry.has_item(itemname):
                operation = itemname_operation_pair[itemname_operation_pair.index(" "):].strip()
                operation = operation[len("received "):].strip().lower()
                self.item_change_processor.add_rule(ItemReceivedCommandRule(itemname, operation, annotation, func))
                return True
            else:
                logging.warning("item " + itemname + " does not exist (trigger " + annotation + ")")

        elif annotation.lower().startswith("item"):
            itemname_operation_pair = annotation[len("item"):].strip()
            itemname = itemname_operation_pair[:itemname_operation_pair.index(" ")].strip()
            if self.item_change_processor.item_registry.has_item(itemname):
                operation = itemname_operation_pair[itemname_operation_pair.index(" "):].strip()
                self.item_change_processor.add_rule(ItemChangedRule(itemname, operation, annotation, func))
                return True
            else:
                logging.warning("item " + itemname + " does not exist (trigger " + annotation + ")")
        return False


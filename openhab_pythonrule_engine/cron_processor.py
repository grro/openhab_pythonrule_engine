import logging
import pycron
import weakref
from time import sleep
from threading import Thread
from datetime import datetime
from openhab_pythonrule_engine.item_registry import ItemRegistry
from openhab_pythonrule_engine.rule import Rule
from openhab_pythonrule_engine.processor import Processor


logging = logging.getLogger(__name__)

class CronRule(Rule):

    def __init__(self, trigger_expression: str, cron: str, func):
        self.cron = cron
        super().__init__(trigger_expression, func)


class CronProcessor(Processor):

    def __init__(self, item_registry: ItemRegistry, listener_ref: weakref):
        self.thread = Thread(target=self.__process, daemon=True)
        self.last_execution = datetime.fromtimestamp(0)
        super().__init__("cron", item_registry, listener_ref)

    def parser(self):
        return CronTriggerParser(self).on_annotation

    def __process(self):
        while self.is_running:
            try:
                if (datetime.now() - self.last_execution).total_seconds() >= 60:  # minimum 60 sec!
                    self.last_execution = datetime.now()
                    for rule in self.rules:
                        if pycron.is_now(rule.cron):
                            self.invoke_rule(rule)
            except Exception as e:
                logging.warning("Error occurred by executing cron", e)
            sleep(5)

    def on_start(self):
        self.thread.start()


class CronTriggerParser:

    def __init__(self, cron_processor: CronProcessor):
        self.cron_processor = cron_processor

    def is_vaild_cron(self, cron: str) -> bool:
        try:
            pycron.is_now(cron)
            return True
        except Exception as e:
            return False

    def on_annotation(self, annotation: str, func) -> bool:
        if annotation.lower().startswith("time cron"):
            cron = annotation[len("time cron"):].strip()
            if self.is_vaild_cron(cron):
                self.cron_processor.add_rule(CronRule(annotation, cron, func))
                return True
            else:
                logging.warning("cron " + cron + " is invalid (syntax error?)")
        return False
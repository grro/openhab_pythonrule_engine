import logging
import pycron
from time import sleep
from threading import Thread
from openhab_pythonrule_engine.item_registry import ItemRegistry
from openhab_pythonrule_engine.trigger import Trigger
from openhab_pythonrule_engine.processor import Processor


class CronTrigger(Trigger):

    def __init__(self, expression: str, cron: str, func):
        self.cron = cron
        super().__init__(expression, func)


class CronProcessor(Processor):

    def __init__(self, item_registry: ItemRegistry, listener):
        self.thread = Thread(target=self.__process, daemon=True)
        super().__init__("cron", item_registry, listener)

    def parser(self):
        return CronTriggerParser(self).on_annotation

    def __process(self):
        while self.is_running:
            try:
                for cron_trigger in self.triggers:
                    if pycron.is_now(cron_trigger.cron):
                        self.process_trigger(cron_trigger)
            except Exception as e:
                logging.warning("Error occurred by executing cron", e)
            sleep(60)  # minimum 60 sec!

    def on_start(self):
        self.thread.start()

    def on_stop(self):
        Thread.join(self.thread)


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
                self.cron_processor.add_trigger(CronTrigger(annotation, cron, func))
                return True
            else:
                logging.warning("cron " + cron + " is invalid (syntax error?)")
        return False
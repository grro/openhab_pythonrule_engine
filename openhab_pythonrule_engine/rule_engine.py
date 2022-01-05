import logging
import os
import sys
import importlib
import pycron
from time import sleep
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import List
from openhab_pythonrule_engine.item_registry import ItemRegistry
from openhab_pythonrule_engine.trigger import TriggerRegistry, CronTrigger, ItemChangedTrigger, SystemEventTrigger, Trigger
from openhab_pythonrule_engine.eventbus_consumer import EventConsumer


class FileSystemListener(FileSystemEventHandler):

    def __init__(self, rule_engine):
        self.rule_engine = rule_engine

    def on_moved(self, event):
        self.rule_engine.unload_module(self.filename(event.src_path))
        self.rule_engine.load_module(self.filename(event.dest_path))

    def on_deleted(self, event):
        self.rule_engine.unload_module(self.filename(event.src_path))

    def on_created(self, event):
        self.rule_engine.load_module(self.filename(event.src_path))

    def on_modified(self, event):
        self.rule_engine.load_module(self.filename(event.src_path))

    def filename(self, path):
        path = path.replace("\\", "/")
        return path[path.rindex("/")+1:]


class CronScheduler:

    def __init__(self):
        self.cron_trigger_by_module = {}
        self.thread = Thread(target=self.__process, daemon=True)

    def add_job(self, cron_trigger: CronTrigger):
        cron_triggers = self.cron_trigger_by_module.get(cron_trigger.module, set())
        cron_triggers.add(cron_trigger)
        self.cron_trigger_by_module[cron_trigger.module] = cron_triggers

    def remove_jobs(self, module: str):
        if module in self.cron_trigger_by_module.keys():
            logging.info("removing all " + str(len(self.cron_trigger_by_module[module])) + " crons of '" + module + "'")
            del self.cron_trigger_by_module[module]

    def __process(self):
        while True:
            for cron_triggers in list(self.cron_trigger_by_module.values()):
                for cron_trigger in list(cron_triggers):
                    if pycron.is_now(cron_trigger.cron):
                        try:
                            logging.debug("executing rule " + cron_trigger.name + " (cron 'Time cron " + cron_trigger.cron + "')")
                            cron_trigger.invoke(ItemRegistry.instance())
                        except Exception as e:
                            logging.warning("Error occurred by executing rule " + cron_trigger.name, e)
            sleep(60)



class Rule:

    def __init__(self, func):
        self.func = func
        self.triggers = []

    @property
    def module(self):
        return self.func.__module__

    @property
    def name(self):
        return self.func.__name__

    def __str__(self):
        text = self.module + ".py#" + self.name
        for trigger in self.triggers:
            text += "\r\n  * " + trigger.expression
            for execution in trigger.last_executions:
                text += "\r\n      * " + str(execution)

        return  text

    def __repr__(self):
        return self.__str__()

class RuleEngine:

    __instance = None

    @staticmethod
    def instance():
        return RuleEngine.__instance

    @staticmethod
    def start_singleton(openhab_uri:str, python_rule_directory: str = "/etc/openhab/automation/rules", user: str = None, pwd: str = None):
        rule_engine = RuleEngine(openhab_uri, python_rule_directory, user, pwd)
        RuleEngine.__instance = rule_engine
        rule_engine.start()

    def __init__(self, openhab_uri:str, python_rule_directory: str, user: str, pwd: str):
        self.__python_rule_directory = python_rule_directory
        logging.info("connecting " + openhab_uri)
        ItemRegistry.new_singleton(openhab_uri, user, pwd)
        self.__event_consumer = EventConsumer(openhab_uri, self)
        self.cron_scheduler = CronScheduler()
        self.trigger_registry = TriggerRegistry()

    def start(self):
        logging.info("rules directory is " + self.__python_rule_directory)
        if self.__python_rule_directory not in sys.path:
            sys.path.insert(0, self.__python_rule_directory)

        for file in os.scandir(self.__python_rule_directory):
            self.load_module(file.name)

        observer = Observer()
        observer.schedule(FileSystemListener(self), self.__python_rule_directory, recursive=False)
        observer.start()

        self.__event_consumer.start()

    def add_cron_trigger(self, trigger: CronTrigger):
        self.trigger_registry.register(trigger)
        self.cron_scheduler.add_job(trigger)

    def add_item_changed_trigger(self, trigger: ItemChangedTrigger):
        self.trigger_registry.register(trigger)

    def add_system_event_trigger(self, trigger: SystemEventTrigger):
        trigger.invoke(ItemRegistry.instance())
        self.trigger_registry.register(trigger)

    def load_module(self, filename: str):
        if filename.endswith(".py"):
            modulename = self.__filename_to_modulename(filename)
            # reload?
            if modulename in sys.modules:
                logging.info("reload '" + filename + "'")
                self.cron_scheduler.remove_jobs(modulename)
                self.trigger_registry.deregister(modulename)
                importlib.reload(sys.modules[modulename])
            else:
                logging.info("load '" + filename + "'")
                importlib.import_module(modulename)

    def unload_module(self, filename: str):
        modulename = self.__filename_to_modulename(filename)
        if modulename in sys.modules:
            logging.info("unload '" + filename + "'")
            self.cron_scheduler.remove_jobs(modulename)
            self.trigger_registry.deregister(modulename)
            del sys.modules[modulename]

    def __filename_to_modulename(self, filename):
        return filename[:-3]

    def on_event(self, event):
        ItemRegistry.instance().on_event(event)
        for item_changed_trigger in self.trigger_registry.get_triggers_by_type(ItemChangedTrigger):
            item_changed_trigger.on_event(event)

    @property
    def rules(self) -> List[Rule]:
        rules = []
        for module in self.trigger_registry.triggers_by_module.keys():
            triggers = self.trigger_registry.triggers_by_module[module]
            for func in [trigger.func for trigger in triggers]:
                rule = Rule(func)
                rules.append(rule)
                for trigger in triggers:
                    if trigger.name == rule.name:
                        rule.triggers.append(trigger)
        return rules
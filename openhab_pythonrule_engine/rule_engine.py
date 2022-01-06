import logging
import os
import sys
import importlib
import pycron
from time import sleep
from threading import Thread
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import List, Set, Optional
from openhab_pythonrule_engine.item_registry import ItemRegistry
from openhab_pythonrule_engine.trigger import TriggerRegistry, CronTrigger, ItemChangedTrigger, SystemEventTrigger, Trigger, Execution
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
        self.__is_running = True
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
        while self.__is_running:
            for cron_triggers in list(self.cron_trigger_by_module.values()):
                for cron_trigger in list(cron_triggers):
                    if pycron.is_now(cron_trigger.cron):
                        try:
                            logging.debug("executing rule " + cron_trigger.name + " (cron 'Time cron " + cron_trigger.cron + "')")
                            cron_trigger.invoke(ItemRegistry.instance())
                        except Exception as e:
                            logging.warning("Error occurred by executing rule " + cron_trigger.name, e)
            sleep(60)  # minimum 60 sec!

    def start(self):
        self.thread.start()

    def stop(self):
        self.__is_running = False
        Thread.join(self.thread)


class Rule:

    def __init__(self, func):
        self.func = func
        self.__triggers = []
        self.__listeners = set()

    @property
    def module(self) -> str:
        return self.func.__module__

    @property
    def name(self) -> str:
        return self.func.__name__

    @property
    def triggers(self) -> List[Trigger]:
        return self.__triggers

    @property
    def last_executions(self) -> List[Execution]:
        executions: list[Execution] = []
        for trigger in self.__triggers:
            for execution in trigger.last_executions:
                executions.append(execution)
        executions.sort(reverse=True)
        return executions

    @property
    def last_execution_date(self) -> Optional[datetime]:
        execution = self.__newest_execution()
        if execution is None:
            return None
        else:
            return execution.datetime

    @property
    def last_trigger(self) -> Optional[Trigger]:
        execution = self.__newest_execution()
        if execution is None:
            return None
        else:
            return execution.trigger

    def __newest_execution(self) -> Optional[Execution]:
        last_execution = None
        for trigger in self.__triggers:
            for execution in trigger.last_executions:
                if last_execution is None or execution.datetime > last_execution.datetime:
                    last_execution = execution
        return last_execution

    def add_listener(self, listener):
        self.__listeners.add(listener)

    def add_trigger(self, trigger):
        self.__triggers.append(trigger)
        trigger.add_listener(self.on_trigger_executed)

    def on_trigger_executed(self, trigger: Trigger):
        for listener in self.__listeners:
            try:
                listener(self)
            except Exception as e:
                logging.warning("error occurred by calling listener", e)

    def __str__(self):
        text = self.module + ".py#" + self.name
        for trigger in self.__triggers:
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
        return rule_engine

    def __init__(self, openhab_uri:str, python_rule_directory: str, user: str, pwd: str):
        self.__python_rule_directory = python_rule_directory
        logging.info("connecting " + openhab_uri)
        ItemRegistry.new_singleton(openhab_uri, user, pwd)
        self.__event_consumer = EventConsumer(openhab_uri, self)
        self.__event_consumer.start()
        self.__cron_scheduler = CronScheduler()
        self.__cron_scheduler.start()
        self.__trigger_registry = TriggerRegistry()

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
        self.__trigger_registry.register(trigger)
        self.__cron_scheduler.add_job(trigger)

    def add_item_changed_trigger(self, trigger: ItemChangedTrigger):
        self.__trigger_registry.register(trigger)

    def add_system_event_trigger(self, trigger: SystemEventTrigger):
        trigger.invoke(ItemRegistry.instance())
        self.__trigger_registry.register(trigger)

    def load_module(self, filename: str):
        if filename.endswith(".py"):
            modulename = self.__filename_to_modulename(filename)
            # reload?
            if modulename in sys.modules:
                logging.info("reload '" + filename + "'")
                self.__cron_scheduler.remove_jobs(modulename)
                self.__trigger_registry.deregister(modulename)
                importlib.reload(sys.modules[modulename])
            else:
                logging.info("load '" + filename + "'")
                importlib.import_module(modulename)

    def unload_module(self, filename: str):
        modulename = self.__filename_to_modulename(filename)
        if modulename in sys.modules:
            logging.info("unload '" + filename + "'")
            self.__cron_scheduler.remove_jobs(modulename)
            self.__trigger_registry.deregister(modulename)
            del sys.modules[modulename]

    def __filename_to_modulename(self, filename):
        return filename[:-3]

    def on_event(self, event):
        ItemRegistry.instance().on_event(event)
        for item_changed_trigger in self.__trigger_registry.get_triggers_by_type(ItemChangedTrigger):
            item_changed_trigger.on_event(event)

    @property
    def rules(self) -> Set[Rule]:
        rules = set()
        for module in self.__trigger_registry.triggers_by_module.keys():
            triggers = self.__trigger_registry.triggers_by_module[module]
            for func in [trigger.func for trigger in triggers]:
                rule = Rule(func)
                rules.add(rule)
                for trigger in triggers:
                    if trigger.name == rule.name:
                        rule.add_trigger(trigger)
        return rules
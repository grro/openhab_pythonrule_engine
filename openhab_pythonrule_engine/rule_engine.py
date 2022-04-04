import json
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
from typing import List, Optional
from openhab_pythonrule_engine.item_registry import ItemRegistry
from openhab_pythonrule_engine.trigger import TriggerRegistry, CronTrigger, ItemTrigger, RuleLoadedTrigger, ManualTrigger, Trigger, Execution
from openhab_pythonrule_engine.eventbus_consumer import EventConsumer, parse_item_event

#logging.basicConfig(format='%(asctime)s %(name)-20s: %(levelname)-8s %(message)s', level="INFO", datefmt='%Y-%m-%d %H:%M:%S')

logging = logging.getLogger(__name__)



class FileSystemListener(FileSystemEventHandler):

    @staticmethod
    def start(rule_engine):
        dir = rule_engine.python_rule_directory
        logging.info("observing rules directory " + dir)
        observer = Observer()
        observer.schedule(FileSystemListener(rule_engine), dir, recursive=False)
        observer.start()
        return observer

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
        self.__cron_listeners = set()
        self.__last_crons = []
        self.cron_trigger_by_module = {}
        self.__is_running = True
        self.thread = Thread(target=self.__process, daemon=True)

    @property
    def last_crons(self) -> List[str]:
        return self.__last_crons

    def add_cron_listener(self, listener):
        self.__cron_listeners.add(listener)

    def add_job(self, cron_trigger: CronTrigger):
        cron_triggers = self.cron_trigger_by_module.get(cron_trigger.module, set())
        cron_triggers.add(cron_trigger)
        self.cron_trigger_by_module[cron_trigger.module] = cron_triggers

    def remove_jobs(self, module: str):
        if module in self.cron_trigger_by_module.keys():
            logging.info("removing all " + str(len(self.cron_trigger_by_module[module])) + " cron jobs of '" + module + "'")
            del self.cron_trigger_by_module[module]

    def __process(self):
        logging.info("cron scheduler started")
        while self.__is_running:
            try:
                for cron_triggers in list(self.cron_trigger_by_module.values()):
                    for cron_trigger in list(cron_triggers):
                        if pycron.is_now(cron_trigger.cron):
                            error = None
                            try:
                                cron_trigger.invoke(ItemRegistry.instance())
                            except Exception as e:
                                logging.warning("Error occurred by executing rule " + cron_trigger.name, e)
                                error = e
                            self.__last_crons.append("[" + datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + "] " + cron_trigger.cron + " -> " + cron_trigger.module + "." + cron_trigger.name + (" " if error is None else "(" + str(error) + ")"))
                            while len(self.__last_crons) > 20:
                                self.__last_crons.pop(0)
                            for listener in self.__cron_listeners:
                                try:
                                    listener()
                                except Exception as e:
                                    logging.warning("Error occurred by calling listener " + str(listener), e)
            except Exception as e:
                logging.warning("Error occurred by executing cron", e)
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
        self.__triggers = sorted(self.__triggers)
        trigger.add_listener(self.on_trigger_executed)

    def execute(self, item_registry: ItemRegistry = ItemRegistry.instance()):
        for trigger in self.triggers:
            if isinstance(trigger, ManualTrigger):
                trigger.invoke(item_registry)
                return

    def on_trigger_executed(self, trigger: Trigger):
        for listener in self.__listeners:
            try:
                listener(self)
            except Exception as e:
                logging.warning("error occurred by calling listener", e)

    def __hash__(self):
        return hash(self.__str__())

    def __eq__(self, other):
        return self.__str__() == other.__str__()

    def __lt__(self, other):
        return self.__str__() < other.__str__()

    def __str__(self):
        return self.module + ".py#" + self.name + " (" + ", ".join(["'" + trigger.expression + "'" for trigger in self.__triggers]) + ")"

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
        self.__listeners = set()
        self.__event_listeners = set()
        self.__last_events = []
        self.__last_handled_events = []
        self.python_rule_directory = python_rule_directory
        logging.info("connecting " + openhab_uri)
        ItemRegistry.new_singleton(openhab_uri, user, pwd)
        self.__event_consumer = EventConsumer(openhab_uri, self)
        self.__cron_scheduler = CronScheduler()
        self.__trigger_registry = TriggerRegistry()

    def add_listener(self, listener):
        self.__listeners.add(listener)

    def add_event_listener(self, listener):
        self.__event_listeners.add(listener)

    def add_cron_listener(self, listener):
        self.__cron_scheduler.add_cron_listener(listener)

    @property
    def last_events(self) -> List[str]:
        return self.__last_events

    @property
    def last_event(self) -> str:
        return self.__last_events[-1]

    @property
    def last_handled_events(self) -> List[str]:
        return self.__last_handled_events

    @property
    def last_handled_event(self) -> str:
        return self.__last_handled_events[-1]

    @property
    def last_crons(self) -> List[str]:
        return self.__cron_scheduler.last_crons

    @property
    def last_cron(self) -> str:
        return self.__cron_scheduler.last_crons[-1]

    def start(self):
        if self.python_rule_directory not in sys.path:
            sys.path.insert(0, self.python_rule_directory)
        for file in os.scandir(self.python_rule_directory):
            self.load_module(file.name)
        FileSystemListener.start(self)
        self.__cron_scheduler.start()
        self.__event_consumer.start()

    def add_trigger(self, trigger: Trigger):
        rules = self.rules
        if trigger.is_valid():
            logging.info(" * " + trigger.name + "(...): trigger '" + trigger.expression + "' has been registered")
            self.__trigger_registry.register(trigger)
            if isinstance(trigger, CronTrigger):
                self.__cron_scheduler.add_job(trigger)
            elif isinstance(trigger, RuleLoadedTrigger):
                trigger.invoke(ItemRegistry.instance())
        else:
            logging.warning("Unsupported function spec " + trigger.module + "#" + trigger.name + " Ignoring it")
        if rules != self.rules:
            for listener in self.__listeners:
                try:
                    listener()
                except Exception as e:
                    logging.warning("error occurred calling rules listener", e)

    def load_module(self, filename: str):
        if filename.endswith(".py"):
            try:
                modulename = self.__filename_to_modulename(filename)
                # reload?
                if modulename in sys.modules:
                    logging.info("reloading '" + filename + "'")
                    self.__cron_scheduler.remove_jobs(modulename)
                    self.__trigger_registry.deregister(modulename)
                    importlib.reload(sys.modules[modulename])
                else:
                    logging.info("loading '" + filename + "'")
                    importlib.import_module(modulename)
            except Exception as e:
                logging.warning("error occurred by (re)loading " + filename, e)

    def unload_module(self, filename: str):
        try:
            modulename = self.__filename_to_modulename(filename)
            if modulename in sys.modules:
                logging.info("unloading '" + filename + "'")
                self.__cron_scheduler.remove_jobs(modulename)
                self.__trigger_registry.deregister(modulename)
                del sys.modules[modulename]
        except Exception as e:
            logging.warning("error occurred by unloading " + filename, e)

    def __filename_to_modulename(self, filename):
        return filename[:-3]

    def on_event(self, event):
        self.__last_events.append("[" + datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + "] " + json.dumps(event, indent=0))
        while len(self.__last_events) > 20:
            self.__last_events.pop(0)
        for listener in self.__event_listeners:
            try:
                listener()
            except Exception as e:
                logging.warning("Error occurred by calling listener " + str(listener), e)

        ItemRegistry.instance().on_event(event)
        triggers: List[ItemTrigger] = self.__trigger_registry.get_triggers_by_type(ItemTrigger)
        item_event = parse_item_event(event)
        if item_event is not None:
            matching_triggers = [trigger for trigger in triggers if trigger.matches(item_event)]
            for item_changed_trigger in matching_triggers:
                error = None
                try:
                    item_changed_trigger.invoke(ItemRegistry.instance())
                except Exception as e:
                    logging.warning("Error occurred by executing rule " + item_changed_trigger.name, e)
                    error = e
                self.__last_handled_events.append("[" + datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + "] " + item_changed_trigger.expression + " -> " + item_changed_trigger.module + "." + item_changed_trigger.name + (" " if error is None else "(" + str(error) + ")"))
                while len(self.__last_handled_events) > 20:
                    self.__last_handled_events.pop(0)
                for listener in self.__event_listeners:
                    try:
                        listener()
                    except Exception as e:
                        logging.warning("Error occurred by calling listener " + str(listener), e)

    @property
    def rules(self) -> List[Rule]:
        rules = set()
        for module in self.__trigger_registry.triggers_by_module.keys():
            triggers = self.__trigger_registry.triggers_by_module[module]
            for func in [trigger.func for trigger in triggers]:
                rule = Rule(func)
                rule.add_trigger(ManualTrigger(func))
                for trigger in triggers:
                    if trigger.name == rule.name:
                        rule.add_trigger(trigger)
                rules.add(rule)
        return sorted(list(rules))

#RuleEngine.start_singleton("http://192.168.1.27:8080", "C:\\workspace\\test", sys.argv[1], sys.argv[2])
#sleep(10000)
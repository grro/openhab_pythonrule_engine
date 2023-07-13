import logging
import os
import sys
import importlib
import weakref
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from openhab_pythonrule_engine.item_registry import ItemRegistry
from openhab_pythonrule_engine.rule import Rule, ExecutionListener
from openhab_pythonrule_engine.cron_processor import CronProcessor
from openhab_pythonrule_engine.item_change_processor import ItemChangeProcessor
from openhab_pythonrule_engine.loaded_rule_processor import RuleLoadedProcessor
from openhab_pythonrule_engine.source_scanner import visit

logging = logging.getLogger(__name__)


class FileSystemListener(FileSystemEventHandler):

    def __init__(self, rule_engine_ref: weakref, dir):
        self.rule_engine_ref = rule_engine_ref
        self.dir = dir
        self.observer = Observer()

    def __unload_module(self, path: str):
        rule_engine = self.rule_engine_ref()
        if rule_engine is not None:
            rule_engine.unload_module(path)

    def __load_module(self, path: str):
        rule_engine = self.rule_engine_ref()
        if rule_engine is not None:
            rule_engine.load_module(path)

    def start(self):
        logging.info("observing rules directory '" + self.dir + "' started")
        for file in os.scandir(self.dir):
            self.__load_module(file.name)
        self.observer.schedule(self, self.dir, recursive=False)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        logging.info("observing rules directory '" + self.dir + "' stopped")

    def on_moved(self, event):
        self.__unload_module(self.filename(event.src_path))
        self.__load_module(self.filename(event.dest_path))

    def on_deleted(self, event):
        self.__unload_module(self.filename(event.src_path))

    def on_created(self, event):
        self.__load_module(self.filename(event.src_path))

    def on_modified(self, event):
        self.__load_module(self.filename(event.src_path))

    def filename(self, path):
        path = path.replace("\\", "/")
        return path[path.rindex("/")+1:]


class RuleEngine(ExecutionListener):

    def __init__(self, openhab_uri:str, python_rule_directory: str, user: str, pwd: str):
        self.is_running = False
        self.openhab_uri = openhab_uri
        self.__item_registry = ItemRegistry(openhab_uri, user, pwd)
        self.__processors = [ItemChangeProcessor(openhab_uri, self.__item_registry, weakref.ref(self)),
                             CronProcessor(self.__item_registry, weakref.ref(self)),
                             RuleLoadedProcessor(self.__item_registry, weakref.ref(self))]
        self.file_system_listener = FileSystemListener(weakref.ref(self), python_rule_directory)
        self.listeners = set()

    def rules(self):
        return [rule for processor in self.__processors for rule in processor.rules]

    def on_executed(self, rule: Rule, error: Exception):
        self.__notify_listener()

    def add_listener(self, listener):
        self.listeners.add(listener)
        self.__notify_listener()

    def __notify_listener(self):
        for listener in self.listeners:
            try:
                listener()
            except Exception as e:
                logging.warning("error occurred calling " + str(listener) + " " + str(e))

    def start(self):
        if not self.is_running:
            logging.info("starting rule engine...")
            self.is_running = True
            if self.python_rule_directory not in sys.path:
                sys.path.insert(0, self.python_rule_directory)
            [processor.start() for processor in self.__processors]
            self.file_system_listener.start()
            logging.info("rule engine started")

    def __del__(self):
        self.stop()

    def stop(self):
        logging.info("stopping rule engine...")
        self.is_running = False
        self.file_system_listener.stop()
        [processor.stop() for processor in self.__processors]
        for module in {rule.module for rule in self.rules()}:
            self.unload_module(module + ".py")
        logging.info("rule engine stopped")

    @property
    def python_rule_directory(self):
        return self.file_system_listener.dir

    def load_module(self, filename: str):
        if filename.endswith(".py"):
            try:
                modulename = self.__filename_to_modulename(filename)
                msg = None
                # reload?
                if modulename in sys.modules:
                    [processor.remove_rules(modulename) for processor in self.__processors]
                    importlib.reload(sys.modules[modulename])
                    msg = "'" + filename + "' reloaded"
                else:
                    importlib.import_module(modulename)
                    msg = "'" + filename + "' loaded for the first time"
                num_annotations = visit(modulename, [processor.parser() for processor in self.__processors])
                if num_annotations > 0:
                    logging.info(msg)
                self.__notify_listener()
            except Exception as e:
                logging.warning("error occurred by (re)loading " + filename + " " + str(e), e)

    def unload_module(self, filename: str, silent: bool = False):
        if filename.endswith(".py"):
            try:
                modulename = self.__filename_to_modulename(filename)
                if modulename in sys.modules:
                    [processor.remove_rules(modulename) for processor in self.__processors]
                    del sys.modules[modulename]
                    if not silent:
                        logging.info("'" + filename + "' unloaded")
                self.__notify_listener()
            except Exception as e:
                logging.warning("error occurred by unloading " + filename + " " + str(e), e)

    def __filename_to_modulename(self, filename):
        return filename[:-3]

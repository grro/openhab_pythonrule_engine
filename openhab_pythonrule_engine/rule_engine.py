import logging
import os
import sys
import importlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from openhab_pythonrule_engine.item_registry import ItemRegistry
from openhab_pythonrule_engine.cron_processor import CronProcessor
from openhab_pythonrule_engine.item_change_processor import ItemChangeProcessor
from openhab_pythonrule_engine.loaded_rule_processor import RuleLoadedProcessor
from openhab_pythonrule_engine.source_scanner import visit



class FileSystemListener(FileSystemEventHandler):

    def __init__(self, rule_engine, dir):
        self.rule_engine = rule_engine
        self.dir = dir
        logging.info("observing rules directory " + dir)
        self.observer = Observer()

    def start(self):
        for file in os.scandir(self.dir):
            self.rule_engine.load_module(file.name)
        self.observer.schedule(self, self.dir, recursive=False)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        for file in os.scandir(dir):
            self.rule_engine.unload_module(file.name)

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



class RuleEngine:

    def __init__(self, openhab_uri:str, python_rule_directory: str, user: str, pwd: str):
        self.is_running = False
        self.openhab_uri = openhab_uri
        logging.info("connecting " + openhab_uri)
        self.loaded_modules = set()
        self.__item_registry = ItemRegistry(openhab_uri, user, pwd)
        self.__processors = [ItemChangeProcessor(openhab_uri, self.__item_registry),
                             CronProcessor(self.__item_registry),
                             RuleLoadedProcessor(self.__item_registry)]
        self.file_system_listener = FileSystemListener(self, python_rule_directory)

    def __del__(self):
        self.stop()

    def start(self):
        if not self.is_running:
            self.is_running = True
            if self.python_rule_directory not in sys.path:
                sys.path.insert(0, self.python_rule_directory)
            [processor.start() for processor in self.__processors]
            self.file_system_listener.start()

    def stop(self):
        self.is_running = False
        self.file_system_listener.stop()
        [processor.stop() for processor in self.__processors]

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
                    [processor.remove_triggers(modulename) for processor in self.__processors]
                    importlib.reload(sys.modules[modulename])
                    msg = "'" + filename + "' reloaded"
                else:
                    importlib.import_module(modulename)
                    msg = "'" + filename + "' loaded for the first time"
                self.loaded_modules.add(filename)
                num_annotations = visit(modulename, [processor.parser() for processor in self.__processors])
                if num_annotations > 0:
                    logging.info(msg)
            except Exception as e:
                logging.warning("error occurred by (re)loading " + filename + " " + str(e), e)

    def unload_module(self, filename: str, silent: bool = False):
        if filename.endswith(".py"):
            try:
                modulename = self.__filename_to_modulename(filename)
                if modulename in sys.modules:
                    if not silent:
                        logging.info("\"unloading\" '" + filename + "'")
                    [processor.remove_triggers(modulename) for processor in self.__processors]
                    del sys.modules[modulename]
                self.loaded_modules.remove(filename)
            except Exception as e:
                logging.warning("error occurred by unloading " + filename + " " + str(e), e)

    def __filename_to_modulename(self, filename):
        return filename[:-3]

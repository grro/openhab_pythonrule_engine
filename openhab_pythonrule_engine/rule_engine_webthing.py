import tornado.ioloop
import logging
from webthing import (Value, Property, Thing, SingleThing, WebThingServer)
from typing import List
from openhab_pythonrule_engine.rule_engine import RuleEngine


logging = logging.getLogger(__name__)


class RuleEngineThing(Thing):

    def __init__(self, description: str, rule_engine: RuleEngine):
        Thing.__init__(
            self,
            'urn:dev:ops:pythonrule_engine-1',
            'python_rule',
            [],
            description
        )

        self.rule_engine = rule_engine

        self.openhab_uri = Value(self.rule_engine.openhab_uri)
        self.add_property(
            Property(self,
                     'openhab_uri',
                     self.openhab_uri,
                     metadata={
                         'title': 'openhab URI',
                         'type': 'string',
                         'description': 'the connected openhab instance',
                         'readOnly': True
                     }))

        self.loaded_modules = Value("")
        self.add_property(
            Property(self,
                     'loaded_modules',
                     self.loaded_modules,
                     metadata={
                         'title': 'loaded modules',
                         'type': 'string',
                         'description': 'list of loaded modules',
                         'readOnly': True
                     }))

        self.last_executed = Value("")
        self.add_property(
            Property(self,
                     'last_executed',
                     self.last_executed,
                     metadata={
                         'title': 'last executed rule',
                         'type': 'string',
                         'description': 'list of last executed rule',
                         'readOnly': True
                     }))

        self.last_failed = Value("")
        self.add_property(
            Property(self,
                     'last_failed',
                     self.last_failed,
                     metadata={
                         'title': 'last failed rule',
                         'type': 'string',
                         'description': 'list of failed executed rule',
                         'readOnly': True
                     }))

        self.ioloop = tornado.ioloop.IOLoop.current()
        self.rule_engine.add_listener(self.on_update)

    def on_update(self):
        self.ioloop.add_callback(self.__handle)

    def __print_module_info(self) -> List[str]:
        func_info = {}
        for rule in self.rule_engine.rules():
            key = rule.module + "#" + rule.function_name
            expressions = func_info.get(key, set())
            expressions.add(rule.trigger_expression)
            func_info[key] = expressions
        sorted_keys = sorted(list(func_info.keys()))
        return [key + " (" + ", ".join(func_info[key]) + ")" for key in sorted_keys]

    def __print_last_executed(self) -> List[str]:
        func_info = {}
        for rule in self.rule_engine.rules():
            if rule.last_executed is not None:
                key = rule.module + "#" + rule.function_name
                execution_times = func_info.get(key, [])
                execution_times.append(rule.last_executed)
                func_info[key] = execution_times
        sorted_keys = sorted(list(func_info.keys()))
        return [key + " (" + sorted(func_info[key])[-1].strftime("%H:%M:%S") + ")" for key in sorted_keys]

    def __print_last_failed(self) -> List[str]:
        func_info = {}
        for rule in self.rule_engine.rules():
            if rule.last_failed is not None:
                key = rule.module + "#" + rule.function_name
                execution_times = func_info.get(key, [])
                execution_times.append(rule.last_failed)
                func_info[key] = execution_times
        sorted_keys = sorted(list(func_info.keys()))
        return [key + " (" + sorted(func_info[key])[-1].strftime("%H:%M:%S") + ")" for key in sorted_keys]

    def __handle(self):
        self.last_executed.notify_of_external_update(", ".join(self.__print_last_executed()))
        self.last_failed.notify_of_external_update(", ".join(self.__print_last_failed()))
        self.loaded_modules.notify_of_external_update(", ".join(self.__print_module_info()))

def run_server(port: int, description: str, rule_engine: RuleEngine):
    rule_engine_webthing = RuleEngineThing(description, rule_engine)
    server = WebThingServer(SingleThing(rule_engine_webthing), port=port, disable_host_validation=True)

    try:
        # start webthing server
        logging.info('starting the server listing on ' + str(port))
        server.start()
    except KeyboardInterrupt:
        logging.info('stopping the server')
        server.stop()
        rule_engine.stop()
        logging.info('done')


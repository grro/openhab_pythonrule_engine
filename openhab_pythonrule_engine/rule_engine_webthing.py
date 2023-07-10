from webthing import (Value, Property, Thing, SingleThing, WebThingServer)
import tornado.ioloop
import logging
from openhab_pythonrule_engine.rule_engine import RuleEngine


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
                         'description': 'the list of loaded modules',
                         'readOnly': True
                     }))

        self.ioloop = tornado.ioloop.IOLoop.current()


    def on_event(self):
        self.ioloop.add_callback(self.__handle)

    def on_cron(self):
        self.ioloop.add_callback(self.__handle)

    def __handle(self):
        self.loaded_modules.notify_of_external_update(", ".join(sorted(list(self.rule_engine.loaded_modules))))


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


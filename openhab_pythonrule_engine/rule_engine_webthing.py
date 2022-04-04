from webthing import (Value, Property, Thing, SingleThing, WebThingServer)
import tornado.ioloop
import logging
from openhab_pythonrule_engine.rule_engine import RuleEngine, Rule


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
        rule_engine.add_event_listener(self.on_event)
        rule_engine.add_cron_listener(self.on_cron)

        self.last_event = Value("")
        self.add_property(
            Property(self,
                     'last_event',
                     self.last_event,
                     metadata={
                         'title': 'last_event',
                         'type': 'string',
                         'description': 'the newest event',
                         'readOnly': True
                     }))

        self.last_handled_event = Value("")
        self.add_property(
            Property(self,
                     'last_handled_event',
                     self.last_handled_event,
                     metadata={
                         'title': 'last_handled_event',
                         'type': 'string',
                         'description': 'the newest handled event',
                         'readOnly': True
                     }))

        self.last_cron = Value("")
        self.add_property(
            Property(self,
                     'last_cron',
                     self.last_cron,
                     metadata={
                         'title': 'last_cron',
                         'type': 'string',
                         'description': 'the newest cron execution',
                         'readOnly': True
                     }))

        self.ioloop = tornado.ioloop.IOLoop.current()


    def on_event(self):
        self.ioloop.add_callback(self.__handle_event)

    def __handle_event(self):
        self.last_event.notify_of_external_update(self.rule_engine.last_event)
        self.last_handled_event.notify_of_external_update(self.rule_engine.last_handled_event)

    def on_cron(self):
        self.ioloop.add_callback(self.__handle_cron)

    def __handle_cron(self):
        self.last_cron.notify_of_external_update(self.rule_engine.last_crons)




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
        logging.info('done')


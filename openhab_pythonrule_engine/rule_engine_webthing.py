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

        self.last_events = Value("")
        self.add_property(
            Property(self,
                     'last_events',
                     self.last_events,
                     metadata={
                         'title': 'last_events',
                         'type': 'string',
                         'description': 'the line break delimited newest events',
                         'readOnly': True
                     }))

        self.last_handled_events = Value("")
        self.add_property(
            Property(self,
                     'last_handled_events',
                     self.last_handled_events,
                     metadata={
                         'title': 'last_handled_events',
                         'type': 'string',
                         'description': 'the line break delimited newest handled events',
                         'readOnly': True
                     }))

        self.last_crons = Value("")
        self.add_property(
            Property(self,
                     'last_crons',
                     self.last_crons,
                     metadata={
                         'title': 'last_crons',
                         'type': 'string',
                         'description': 'the line break delimited newest cron executions',
                         'readOnly': True
                     }))

        self.ioloop = tornado.ioloop.IOLoop.current()


    def on_event(self):
        self.ioloop.add_callback(self.__handle_event)

    def __handle_event(self):
        self.last_events.notify_of_external_update('\r\n'.join(self.rule_engine.last_events))
        self.last_handled_events.notify_of_external_update('\r\n'.join(self.rule_engine.last_handled_events))

    def on_cron(self):
        self.ioloop.add_callback(self.__handle_cron)

    def __handle_cron(self):
        self.last_crons.notify_of_external_update('\r\n'.join(self.rule_engine.last_crons))




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


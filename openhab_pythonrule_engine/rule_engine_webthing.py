from webthing import (SingleThing, Value, Property, Thing, MultipleThings, WebThingServer)
import tornado.ioloop
import logging
from openhab_pythonrule_engine.rule_engine import RuleEngine, Rule


class RuleThing(Thing):

    def __init__(self, description: str, rule: Rule):
        Thing.__init__(
            self,
            'urn:dev:ops:pythonrule-1',
            'python_rule',
            [],
            description
        )

        self.name = Value(rule.module + "." + rule.name)
        self.add_property(
            Property(self,
                     'name',
                     self.name,
                     metadata={
                         'title': 'name',
                         'type': 'string',
                         'description': 'the rule name',
                         'readOnly': True
                     }))

        self.ioloop = tornado.ioloop.IOLoop.current()
        



def run_server(port: int, description: str, rule_engine: RuleEngine):
    rule_webthings = [RuleThing(description, rule) for rule in rule_engine.rules]
    server = WebThingServer(MultipleThings(rule_webthings, 'rule'), port=port, disable_host_validation=True)

    try:
        # start webthing server
        logging.info('starting the server listing on ' + str(port))
        server.start()
    except KeyboardInterrupt:
        logging.info('stopping the server')
        server.stop()
        logging.info('done')


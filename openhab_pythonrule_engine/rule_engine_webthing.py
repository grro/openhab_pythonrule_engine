from webthing import (Value, Property, Thing, MultipleThings, WebThingServer)
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

        self.rule = rule
        rule.add_listener(self.on_rule_executed)

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

        self.triggers = Value(", " .join([trigger.expression for trigger in rule.triggers]))
        self.add_property(
            Property(self,
                     'triggers',
                     self.triggers,
                     metadata={
                         'title': 'Last assigned triggers',
                         'type': 'string',
                         'description': 'The comma-separated trigger names',
                         'readOnly': True,
                     }))

        self.execute = Value(False, self.__execute)
        self.add_property(
            Property(self,
                     'execute',
                     self.name,
                     metadata={
                         '@type': 'BooleanProperty',
                         'title': 'execute',
                         'type': 'boolean',
                         'description': 'triggers the rule manually',
                         'readOnly': False
                     }))

        self.history = Value("\r\n" .join([str(execution) for execution in rule.last_executions]))
        self.add_property(
            Property(self,
                     'history',
                     self.history,
                     metadata={
                         'title': 'The newest trigger executions',
                         'type': 'string',
                         'description': 'The linebreak-separated newest trigger executions',
                         'readOnly': True,
                     }))


        self.last_execution_date = Value("" if rule.last_execution_date is None else rule.last_execution_date.isoformat())
        self.add_property(
        Property(self,
                 'last_execution_date',
                 self.last_execution_date,
                 metadata={
                     'title': 'Last execution date of the rule',
                     'type': 'string',
                     'description': 'The date of the last execution (iso 8601 string)',
                     'readOnly': True,
                 }))

        self.last_trigger = Value("" if rule.last_trigger is None else rule.last_trigger.expression)
        self.add_property(
            Property(self,
                     'last_executed_trigger',
                     self.last_trigger,
                     metadata={
                         'title': 'Last executed trigger of this rule',
                         'type': 'string',
                         'description': 'The trigger name',
                         'readOnly': True,
                     }))

        self.ioloop = tornado.ioloop.IOLoop.current()

    def __execute(self, do_execute: bool):
        if do_execute:
            self.rule.execute()
            self.execute.notify_of_external_update(False)

    def on_rule_executed(self, rule):
        self.ioloop.add_callback(self.__sync_props)

    def __sync_props(self):
        self.last_execution_date.notify_of_external_update("" if self.rule.last_execution_date is None else self.rule.last_execution_date.isoformat())
        self.last_trigger.notify_of_external_update("" if self.rule.last_trigger is None else self.rule.last_trigger.expression)
        self.triggers.notify_of_external_update(", " .join([trigger.expression for trigger in self.rule.triggers]))
        self.history.notify_of_external_update("\r\n" .join([str(execution) for execution in self.rule.last_executions]))


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


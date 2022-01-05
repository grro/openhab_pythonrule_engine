import logging
from openhab_pythonrule_engine.item_registry import ItemRegistry
from openhab_pythonrule_engine.rule_engine import CronTrigger, ItemChangedTrigger, SystemEventTrigger, RuleEngine


def when(target: str):
    """
    Examples:
        .. code-block::
            @when("Time cron 55 55 5 * * ?")
            @when("Item gMotion_Sensors changed")
            @when("Rule loaded")
    Args:
        target (string): the `rules DSL-like formatted trigger expression <https://www.openhab.org/docs/configuration/rules-dsl.html#rule-triggers>`_
            to parse
    """

    if target.lower().startswith("item"):
        itemname_operation_pair = target[len("item"):].strip()
        itemname = itemname_operation_pair[:itemname_operation_pair.index(" ")].strip()

        if ItemRegistry.instance().has_item(itemname):
            operation = itemname_operation_pair[itemname_operation_pair.index(" "):].strip()

            def decorated_method(function):
                logging.info(" * " + function.__name__ + ": register trigger '" + target + "'")
                trigger = ItemChangedTrigger(itemname, operation, target, function)
                if trigger.is_valid():
                    RuleEngine.instance().add_item_changed_trigger(trigger)
                else:
                    logging.warning("Unsupported function spec " + str(function) + " Ignoring it")
                return function

            return decorated_method
        else:
            logging.warning("item " + itemname + " does not exist (trigger " + target + ")")


    elif target.lower().startswith("time cron"):
        cron = target[len("time cron"):].strip()

        def decorated_method(function):
            logging.info(" * " + function.__name__ + ": register cron    '" + target + "'")
            trigger = CronTrigger(cron, target, function)
            if trigger.is_valid():
                RuleEngine.instance().add_cron_trigger(trigger)
            else:
                logging.warning("Unsupported function spec " + str(function) + " Ignoring it")
            return function

        return decorated_method

    elif target.lower().strip() == "rule loaded":

        def decorated_method(function):
            logging.info(" * " + function.__name__ + ": register system  '" + target + "'")
            trigger = SystemEventTrigger(target, function)
            if trigger.is_valid():
                RuleEngine.instance().add_system_event_trigger(trigger)
            else:
                logging.warning("Unsupported function spec " + str(function) + " Ignoring it")
            return function

        return decorated_method

    else:
        logging.warning("unsupported expression " + target + " ignoring it")
        def decorated_method(function):
            return function
        return decorated_method

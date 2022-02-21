import logging
from openhab_pythonrule_engine.item_registry import ItemRegistry
from openhab_pythonrule_engine.rule_engine import RuleEngine
from openhab_pythonrule_engine.trigger import CronTrigger, ItemReceivedCommandTrigger, ItemChangedTrigger, RuleLoadedTrigger



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

    target = target.strip()


    if RuleEngine.instance() is None:

        def decorated_method(function):
            return function
        return decorated_method

    elif target.lower().startswith("item") and (target.lower().endswith(" received command on") or target.lower().endswith(" received command off")):
        itemname_operation_pair = target[len("item"):].strip()
        itemname = itemname_operation_pair[:itemname_operation_pair.index(" ")].strip()

        if ItemRegistry.instance().has_item(itemname):
            operation = itemname_operation_pair[itemname_operation_pair.index(" "):].strip()
            operation = operation[len("received "):].strip().lower()

            def decorated_method(function):

                trigger = ItemReceivedCommandTrigger(itemname, operation, target, function)
                RuleEngine.instance().add_trigger(trigger)
                return function

            return decorated_method
        else:
            logging.warning("item " + itemname + " does not exist (trigger " + target + ")")

    elif target.lower().startswith("item"):
        itemname_operation_pair = target[len("item"):].strip()
        itemname = itemname_operation_pair[:itemname_operation_pair.index(" ")].strip()

        if ItemRegistry.instance().has_item(itemname):
            operation = itemname_operation_pair[itemname_operation_pair.index(" "):].strip()

            def decorated_method(function):
                trigger = ItemChangedTrigger(itemname, operation, target, function)
                RuleEngine.instance().add_trigger(trigger)
                return function

            return decorated_method
        else:
            logging.warning("item " + itemname + " does not exist (trigger " + target + ")")

    elif target.lower().strip() == "rule loaded":

        def decorated_method(function):
            trigger = RuleLoadedTrigger(target, function)
            RuleEngine.instance().add_trigger(trigger)
            return function

        return decorated_method

    elif target.lower().startswith("time cron"):
        cron = target[len("time cron"):].strip()

        def decorated_method(function):
            trigger = CronTrigger(cron, target, function)
            RuleEngine.instance().add_trigger(trigger)
            return function

        return decorated_method

    else:
        logging.warning("unsupported expression " + target + " ignoring it")
        def decorated_method(function):
            return function
        return decorated_method

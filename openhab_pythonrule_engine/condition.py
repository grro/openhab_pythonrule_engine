

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

    def decorated_method(function):
        return function
    return decorated_method

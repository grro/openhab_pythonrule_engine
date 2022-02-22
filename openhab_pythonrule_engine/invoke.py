import inspect
import logging
from logging import Logger


from openhab_pythonrule_engine.item_registry import ItemRegistry



logging = logging.getLogger(__name__)


class Invoker():

    TYPE_SINGLE_PARAM_ITEMREGISTRY = "TYPE_SINGLE_PARAM_ITEMREGISTRY"

    def __init__(self, func, type: str):
        self.__func = func
        self.name = func.__name__
        self.fullname = func.__module__ + "#" + self.name
        self.__type = type

    @staticmethod
    def create(func):
        type = ""
        spec = inspect.getfullargspec(func)

        # one argument ItemRegistry
        if len(spec.args) == 1:
            type = Invoker.TYPE_SINGLE_PARAM_ITEMREGISTRY
            if spec.args[0] in spec.annotations:
                if spec.annotations[spec.args[0]] != ItemRegistry:
                    logging.warning("parameter " + str(spec.args[0]) + " is of type " + str(spec.annotations[spec.args[0]]) + ". " +
                                    str(spec.annotations[spec.args[0]]) + " is not supported (supported: ItemRegistry)")
                    return None
            else:
                logging.warning("assuming that parameter " + spec.args[0] + " is of type ItemRegistry. " \
                                "Please use type hints such as " + func.__name__ + "(" + spec.args[0]  + ": ItemRegistry)")
        return Invoker(func, type)

    def invoke(self, item_registry: ItemRegistry):
        try:
            if self.__type ==  self.TYPE_SINGLE_PARAM_ITEMREGISTRY:
                self.__func(item_registry)
            else:
                self.__func()
        except Exception as e:
            raise Exception("Error occurred executing function " + self.fullname+ "(...)") from e

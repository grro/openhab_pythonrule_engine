from invoke import Invoker
from item_registry import ItemRegistry



class SystemRegistry:

    __instance = None

    @staticmethod
    def instance():
        if SystemRegistry.__instance == None:
            SystemRegistry.__instance = SystemRegistry()
        return SystemRegistry.__instance

    def register(self, func):
        Invoker.create(func).invoke(ItemRegistry.instance())

    def deregister(self, module):
        pass

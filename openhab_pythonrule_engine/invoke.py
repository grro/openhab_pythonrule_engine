import inspect
import logging
from typing import Optional, List
from queue import Queue, Empty
from datetime import datetime, timedelta
from threading import Thread, Lock
from openhab_pythonrule_engine.item_registry import ItemRegistry




class Invoker():

    TYPE_SINGLE_PARAM_ITEMREGISTRY = "TYPE_SINGLE_PARAM_ITEMREGISTRY"

    def __init__(self, func, type: str):
        self._func = func
        self.name = func.__name__
        self.fullname = func.__module__ + "#" + self.name
        self.__type = type

    @property
    def id(self) -> str:
        return self.fullname

    def invoke(self, item_registry: ItemRegistry):
        try:
            if self.__type ==  self.TYPE_SINGLE_PARAM_ITEMREGISTRY:
                self._func(item_registry)
            else:
                self._func()
        except Exception as e:
            raise Exception("Error occurred executing function " + self.fullname + "(...)") from e



class AsncInvoker(Invoker):

    def __init__(self, invoker_manager, func, type: str):
        self.invoker_manager = invoker_manager
        super().__init__(func, type)

    def invoke(self, item_registry: ItemRegistry):
        self.invoker_manager.initiate_invoke(self, item_registry)

    def real_invoke(self, item_registry: ItemRegistry):
        super().invoke(item_registry)

    def __str__(self):
        return self._func.__module__ + "#" + self._func.__name__



class InvocationRunner:

    def __init__(self, invoker: AsncInvoker, item_registry : ItemRegistry):
        self.invoker = invoker
        self.item_registry = item_registry

    @property
    def id(self) -> str:
        return self.invoker.id

    def invoke(self):
        self.invoker.real_invoke(self.item_registry)

    def __str__(self):
        return str(self.invoker)

class InvokerManager:

    def __init__(self, num_runners: int = 10):
        self.is_running = True
        self.num_runners = num_runners
        self.__listeners = set()
        self.__lock = Lock()
        self.__running_invocations = {}
        self.__queue = Queue()

    def running_invocations(self) -> List[str]:
        with self.__lock:
            return [str(invocation_runner) for invocation_runner in self.__running_invocations.values()]

    def add_listener(self, listener):
        self.__listeners.add(listener)
        self.__notify_listener()

    def __notify_listener(self):
        for listener in self.__listeners:
            try:
                listener()
            except Exception as e:
                logging.warning("error occurred calling " + str(listener) + " " + str(e))

    def start(self):
        [Thread(target=self.loop_invoke_runner, daemon=True, args=(i,)).start() for i in range(0, self.num_runners)]

    def stop(self):
        self.is_running = False

    def initiate_invoke(self, invoker: AsncInvoker, item_registry : ItemRegistry):
        self.__queue.put(InvocationRunner(invoker, item_registry))

    def register_running(self, invocation_runner : InvocationRunner) -> Optional[datetime]:
        try:
            with self.__lock:
                if invocation_runner.id in self.__running_invocations.keys():
                    return self.__running_invocations[invocation_runner.id]
                else:
                    self.__running_invocations[invocation_runner.id] = datetime.now()
                    return None
        finally:
            self.__notify_listener()

    def deregister_running(self, invocation_runner : InvocationRunner):
        try:
            with self.__lock:
                self.__running_invocations.pop(invocation_runner.id, None)
        finally:
            self.__notify_listener()

    def loop_invoke_runner(self, runner_id: int):
        while self.is_running:
            try:
                invocation_runner = self.__queue.get(timeout=3)
                running_since = self.register_running(invocation_runner)
                if running_since is None:
                    try:
                        logging.debug("[runner" + str(runner_id) + "] invoking " + str(invocation_runner))
                        invocation_runner.invoke()
                    except Exception as e:
                        logging.warning("[runner" + str(runner_id) + "] error occurred calling " + str(invocation_runner) + " " + str(e))
                    finally:
                        self.deregister_running(invocation_runner)
                else:
                    elapsed_min = round((datetime.now() - running_since).total_seconds() / 60, 1)
                    if elapsed_min > 2:
                        logging.warning("[runner" + str(runner_id) + "] reject invoking " + str(invocation_runner) + " Invocation hangs (since " + str(elapsed_min) + " min)")
                    else:
                        logging.debug("[runner" + str(runner_id) + "] reject invoking " + str(invocation_runner) + " Invocation is already running (since " + str(elapsed_min) + " min)")
            except Empty as e:
                pass
            except Exception as e:
                logging.warning("[runner" + str(runner_id) + "] error occurred " + str(e))

    def new_invoker(self, func):
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
        #return Invoker(func, type)
        return AsncInvoker(self, func, type)



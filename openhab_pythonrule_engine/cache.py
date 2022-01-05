import time


class Cache:

    def __init__(self):
        self.cache = {}

    def clear(self):
        self.cache.clear()

    def read_entry(self,name:str, max_ttl_sec: int = 60):
        if name in self.cache.keys():
            value_time_pair = self.cache[name]
            if (value_time_pair[1] + max_ttl_sec) > time.time():
                return value_time_pair[0]
            else:
                self.cache.pop(name)
        return None

    def add_enry(self, name, value):
        self.cache[name] = (value, time.time())

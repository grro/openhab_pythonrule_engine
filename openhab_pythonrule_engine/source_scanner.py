import inspect
import sys
from typing import List

def visit(modulename: str, visitors: List) -> int:
    num_notations = 0
    try:
        for func in inspect.getmembers(sys.modules[modulename], inspect.isfunction):
            num_notations += process_meta_data_annotation(func, visitors)
    except Exception as e:
        print(e)
    return num_notations

def process_meta_data_annotation(func, visitors: List) -> int:
    num_notations = 0
    source = inspect.getsource(func[1])
    index = source.find("def ")
    for line in source[:index].strip().splitlines():
        line = line.strip()
        if line.startswith("@when("):
            startIdx = len("@when(")
            endIdx = line.index(')', startIdx)
            ano = line[startIdx: endIdx].strip().strip('"')
            for visitor in visitors:
                if visitor(ano, func[1]):
                    num_notations += 1
    return num_notations
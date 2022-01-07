import logging
from time import sleep
from openhab_pythonrule_engine.rule_engine import RuleEngine



logging.basicConfig(format='%(asctime)s %(name)-20s: %(levelname)-8s %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
logging.getLogger('sseclient').disabled = True
logging.getLogger('urllib3.connectionpool').disabled = True

def listener():
    for rule in rule_engine.rules:
        print(str(rule))


rule_engine = RuleEngine.start_singleton("http://192.168.1.27:8080/", "C:\\workspace\\\\openhab_rules", "grro", "Stabilo33!")
rule_engine.add_listener(listener)

sleep(390000)
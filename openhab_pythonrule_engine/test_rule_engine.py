import logging
from time import sleep
from rule_engine import RuleEngine



logging.basicConfig(format='%(asctime)s %(name)-20s: %(levelname)-8s %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
logging.getLogger('sseclient').disabled = True
logging.getLogger('urllib3.connectionpool').disabled = True


#rule_engine = RuleEngine.new_singleton("http://localhost:8080/", "C:\\workspace\\\\openhab_rules", "grro", "Stabilo33!", "C:\\workspace\\\\openhab_rules")
rule_engine = RuleEngine.new_singleton("http://192.168.1.27:8080/", "C:\\workspace\\\\openhab_rules", "grro", "Stabilo33!")
rule_engine.start()

'''
for i in range(0, 10000):
    sleep(5)
    print("")
    for rule in rule_engine.rules:
        print(str(rule))
'''
sleep(1222222)
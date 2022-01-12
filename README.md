# OpenHab python rule engine
A python 3.x rule engine for OpenHAB. This rule engine allows defining rule by using python 3.x. 

**Please consider that the [OpenHAB username/password auhentication](https://www.openhab.org/docs/configuration/restdocs.html) (basic authentication) needs to
be enabled in the org.openhab.restauth settings**


To run this software you may use Docker or [PIP](https://realpython.com/what-is-pip/) package manager such as shown below

**Docker approach**
```
sudo docker run -e openhab_uri=http://192.168.1.17:8080 -e user=me -e pwd=secret -v /etc/openhab2/automation/rules/python:/rules grro/pythonrule_engine 
```

**PIP approach**
```
sudo pip install openhab-pythonrule-engine
```

After this installation you may start the rule engine inside your python code or via command line using
```
sudo pyrule --command listen --openhab_uri http://localhost:8080 --python_rule_directory /etc/openhab2/automation/rules/python --user me --pwd secret
```
Here, the rule engine will connect the openhab instance running on the local machine on port 8080. Furthermore, the directory /etc/openhab2/automation/rules/python will be used to scan for python-based rules

By running a *systemd-based Linux distribution* you may use the *register* command to register and start the rule engine as systemd unit.
By doing this the rule engine will be started automatically on boot. Starting the server manually using the *listen* command is no longer necessary.
```
sudo pyrule --command register --openhab_uri http://localhost:8080 --python_rule_directory /etc/openhab2/automation/rules/python --user me --pwd secret
```  


**Rules**

To trigger a rule methode the @when decorator will be used. Currently
 * Cron expressions are supported as well as
 * Item change trigger 
as shown below 

If the method defines a (single!) argument, the item_registry object will be injected automatically. The item_registry cann be used 
to get item state as well as to update item state. By setting the state the data value will be auto converted into the item specific data type 

Example: **my_rule.py** (located within /etc/openhab2/automation/rules/python)
```python
from openhab_pythonrule_engine.condition import when
from openhab_pythonrule_engine.item_registry import ItemRegistry


@when('Time cron */1 * * * *')  # every 1 minute
@when('Item PhoneLisaLastSeen changed')
@when('Item PhoneJoeLastSeen changed')
def update_persence_based_on_phone_seen(item_registry: ItemRegistry):
    last_time_present = item_registry.get_state_as_datetime('LastDateTimePresence')
    for phone_name in item_registry.get_group_membernames('Phones'):
        last_seen = item_registry.get_state_as_datetime(phone_name)
        if last_seen > last_time_present:
            last_time_present = last_seen
    item_registry.set_state('LastDateTimePresence', last_time_present)
```

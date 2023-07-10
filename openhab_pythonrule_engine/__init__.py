from openhab_pythonrule_engine.rule_engine_webthing import run_server
from openhab_pythonrule_engine.app import App
from openhab_pythonrule_engine.rule_engine import RuleEngine
from string import Template



PACKAGENAME = 'openhab_pythonrule_engine'
ENTRY_POINT = "pyrule"
DESCRIPTION = "Openhab python rule engine"



UNIT_TEMPLATE = Template('''
[Unit]
Description=$packagename
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$entrypoint --command listen --port $port --openhab_uri $openhab_uri --python_rule_directory $python_rule_directory --user $user --pwd $pwd    
SyslogIdentifier=$packagename
StandardOutput=syslog
StandardError=syslog
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
''')




class InternetApp(App):

    def do_add_argument(self, parser):
        parser.add_argument('--openhab_uri', metavar='openhab_uri', required=False, type=str, default="http://localhost:8080", help='the openhab uri such as http://localhost:8080')
        parser.add_argument('--python_rule_directory', metavar='python_rule_directory', required=False, type=str, default="/etc/openhab/automation/rules/python", help='the python_rule_directory such as /etc/openhab/automation/rules/python')
        parser.add_argument('--user', metavar='user', required=False, type=str, default="anonymous", help='the user name')
        parser.add_argument('--pwd', metavar='pwd', required=False, type=str, default="anonymous", help='the password')

    def do_additional_listen_example_params(self):
        return "--openhab_uri http://localhost:8080 --python_rule_directory /etc/openhab/automation/rules/python --user me --pwd secret"

    def do_process_command(self, command:str, port: int, verbose: bool, args) -> bool:
        if command == 'listen' and (args.openhab_uri is not None) \
                               and (args.python_rule_directory is not None) \
                               and (args.user is not None) \
                               and (args.pwd is not None):
            rule_engine = RuleEngine(args.openhab_uri, args.python_rule_directory, args.user, args.pwd)
            rule_engine.start()
            run_server(port, self.description, rule_engine)
            return True
        elif args.command == 'register' and \
             args.openhab_uri is not None and \
             args.python_rule_directory is not None and \
             args.user is not None and \
             args.pwd is not None:
            print("register " + self.packagename + " on port " + str(args.port))
            unit = UNIT_TEMPLATE.substitute(packagename=self.packagename,
                                            entrypoint=self.entrypoint,
                                            port=port,
                                            openhab_uri=args.openhab_uri,
                                            python_rule_directory=args.python_rule_directory,
                                            user=args.user,
                                            pwd=args.pwd,
                                            verbose=verbose)
            self.unit.register(port, unit)
            return True
        else:
            return False

def main():
    InternetApp(PACKAGENAME, ENTRY_POINT, DESCRIPTION).handle_command()


if __name__ == '__main__':
    main()



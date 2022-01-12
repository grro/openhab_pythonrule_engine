FROM python:3.9
#FROM python:3.9.1-alpine

ENV openhab_uri "http://localhost:8080"
ENV python_rule_directory "/rules"
ENV user "anonymous"
ENV pwd "anonymous"


LABEL org.label-schema.schema-version="1.0" \
      org.label-schema.name="pythonrule_engine" \
      org.label-schema.description=" " \
      org.label-schema.url="https://github.com/grro/openhab_pythonrule_engine" \
      org.label-schema.docker.cmd="docker run -e openhab_uri=http://192.168.1.17:8080 -e user=me -e pwd=secret -v /etc/openhab2/automation/rules/python:/rules grro/pythonrule_engine"


ADD . /tmp/
WORKDIR /tmp/
RUN  python /tmp/setup.py install
RUN  python /tmp/setup.py bdist_wheel
WORKDIR /
RUN rm -r /tmp/

CMD pyrule --command listen --port 9070 --openhab_uri $openhab_uri --python_rule_directory "/rules" --user $user --pwd $pwd

# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

from datadog_checks.base import AgentCheck, ConfigurationError

EPOCH = datetime(1970, 1, 1)


class Bind9Check(AgentCheck):
    BIND_SERVICE_CHECK = "bind9.can_connect"
    QUERY_ARRAY = ["opcode", "qtype", "nsstat", "zonestat", "resstat", "sockstat"]

    def check(self, instance):
        dns_url = instance.get('url')

        if not dns_url:
            raise ConfigurationError('The statistic channel URL must be specified in the configuration')

        self.service_check(self.BIND_SERVICE_CHECK, AgentCheck.OK, message='Connection to %s was successful' % dns_url)

        root = self.getStatsFromUrl(dns_url)
        self.collectTimeMetric(root, 'boot-time')
        self.collectTimeMetric(root, 'config-time')
        self.collectTimeMetric(root, 'current-time')

        for counter in self.QUERY_ARRAY:
            self.collectServerMetric(root[0], counter)

        if root.find(".//statistics").attrib.values()[0] == '2.2':
            self.collectServerMetric2(root)

    def getStatsFromUrl(self, dns_url):
        try:
            response = requests.get(dns_url)
            response.raise_for_status()
        except Exception:
            self.service_check(self.BIND_SERVICE_CHECK, AgentCheck.CRITICAL, message="stats cannot be taken")
            raise

        root = ET.fromstring(response.text)
        return root

    def DateTimeToEpoch(self, DateTime):
        # Ignore time zone
        DateTime = DateTime[:19]
        return int((datetime.strptime(DateTime, '%Y-%m-%dT%H:%M:%S') - EPOCH).total_seconds())

    def collectTimeMetric(self, root, metricName):
        for name in root.iter(metricName):
            self.SendMetricsToAgent(metricName, self.DateTimeToEpoch(name.text))

    def collectServerMetric(self, root, queryType):
        if root.find(".//statistics").attrib.values()[0] == '2.2':
            for counter in root.iter(queryType):
                self.SendMetricsToAgent('{}_{}'.format(queryType, counter.find('name').text), counter.find('counter').text)
        else:
            for counter in root.iter("counters"):
                if counter.get('type') == queryType:
                    for query in counter:
                        self.SendMetricsToAgent('{}_{}'.format(queryType, query.get('name')), query.text)

    def collectServerMetric2(self, root):
        root = root.find('bind/statistics')
        for counter in root.findall('server/queries-in/rdtype'):
            self.SendMetricsToAgent('{}_{}'.format('queries_in', counter.find('name').text),
                counter.find('counter').text
            )

        for counter in root.find('memory/summary').getchildren():
            self.SendMetricsToAgent('{}_{}'.format('memory', counter.tag),
                int(counter.text)
            )

        for counter in root.findall('views/view/cache/rrset'):
            self.SendMetricsToAgent('{}_{}'.format('cache_rrset',
                counter.find('name').text.replace('!', 'NOT_')),
                counter.find('counter').text)

    def SendMetricsToAgent(self, metricName, metricValue):
        self.gauge('bind9.{}'.format(metricName), metricValue)

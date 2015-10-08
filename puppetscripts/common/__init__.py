#   Copyright 2015 Indeed
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import logging
import json
from datetime import datetime, timedelta

class ElasticConfig(object):
    def __init__(self,
                hosts=['localhost'],
                port=9200,
                index_pattern='%Y.%m.%d',
                lookback=7,
                username=None,
                password=None,
                environment="production"
                ):
        self.hosts = hosts
        self.port = port
        self.index_pattern = index_pattern
        self.lookback = lookback
        self.username = username
        self.password = password
        self.environment = environment

def LoadElasticConfig(application):
    home = os.getenv("HOME")
    local_file = '{0}/.{1}.conf'.format(home, application)
    global_file = '/etc/{0}/{0}.conf'.format(application)
    if os.path.isfile(local_file):
        # load local configuration
        logging.info("Found local file {0}".format(local_file))
        esconfig = _load_config_file(local_file)
    elif os.path.isfile(global_file):
        # load global configuration
        logging.info("Found global file {0}".format(global_file))
        esconfig = _load_config_file(global_file)
    else:
        esconfig = ElasticConfig()
    return esconfig


def _load_config_file(f):
    j = ''
    with open(f, 'r') as handle:
        j = handle.read()
    esconfig = ElasticConfig(**(json.loads(j)))
    return esconfig

# Move to keep more indexes and have a weekly alias or just pull
# previous week
def get_indexes(lookback, pattern):
    index = 'logstash-{0}'
    indices = []
    today = datetime.utcnow()
    indices.append(index.format(today.strftime(pattern)))
    for i in range(1, lookback):
        indices.append(index.format((today - timedelta(days=i)).strftime(pattern)))
    return indices

def build_query(fqdn, environment):
    print fqdn
    print environment
    query = {
        "size":1,
        "filter": {
            "bool": {
                "must": [
                    {
                        "term": {
                            "host":fqdn,
                        }
                    },
                    {
                        "term": {
                            "environment":environment,
                        }
                    }
                ]
            }
        },
        "sort": [{"@timestamp":{"order":"desc"}}]
    }
    return query

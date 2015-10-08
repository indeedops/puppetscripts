#!/usr/bin/python
#
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

import sys
import multiprocessing
import time
import urllib3
import argparse
import logging
import hashlib
from pyelasticsearch import ElasticSearch

try:
    from puppetscripts import common
except ImportError, ie:
    import common

urllib3.disable_warnings()

parser = argparse.ArgumentParser(description="Query Elasticsearch to analyze the state of Puppet runs across all nodes.")

parser.add_argument('-v','--verbose',
                    action="store_const",
                    const=True,
                    dest="verbose",
                    help="Verbose mode.  Prints more information"
                    )

parser.add_argument('-u','--unresponsive',
                    action="store",
                    type=int,
                    dest="unresponsive",
                    metavar='THRESHOLD',
                    help="Print nodes that are unresponsive sorted by most out-of-sync nodes. Pass argument in minutes for threshold."
                    )

parser.add_argument('-i','--idempotent',
                    action="store_const",
                    const=True,
                    dest="idempotent",
                    help="Tracks down nodes violating idempotency."
                    )

parser.add_argument('-c','--catalog-failure',
                    action="store_const",
                    const=True,
                    dest="failures",
                    help="Prints all nodes where the last run failed catalog compilation."
                    )

parser.add_argument('-r','--resources',
                    action="store_const",
                    const=True,
                    dest="resources",
                    help="Prints statistics about resources causing the most failures."
                    )

parser.add_argument('-n','--nodes',
                    action="store_const",
                    const=True,
                    dest="nodes",
                    help="Prints statistics about nodes: nodes with the most resource failures"
                    )


def search(query):
    pattern = elastic_config.index_pattern
    lookback = elastic_config.lookback
    indices = common.get_indexes(lookback, pattern)
    hosts = elastic_config.hosts
    port = elastic_config.port
    username = elastic_config.username
    password = elastic_config.password
    environment = elastic_config.environment
    es = ElasticSearch(hosts, port=443, username=username, password=password)
    try:
        logging.info("Querying Elasticsearch using {0}".format(query))
        doc = es.search(query, index=indices)
        return doc
    except:
        logging.error("Unexpected error searching for {0}. Passing".format(query))
        pass

def get_node_list():
    """Returns a list of unique nodes in Elasticsearch"""
    node_list = []
    query = {
        "size":0,
        "query": {
            "filtered": {
                "filter": {
                    "exists": {
                        "field": "environment"
                    }
                }
            }
        },
        "aggs": {
            "by_hosts": {
                "terms": {
                    "size": 0,
                    "field": "host",
                }
            }
        },
        "sort": [{"@timestamp":{"order":"desc"}}]
    }
    doc = search(query)
    logging.info("Returned {0} documents".format(doc['hits']['total']))
    document = doc['aggregations']['by_hosts']['buckets']
    for bucket in document:
        node_list.append(bucket['key'])

    return node_list

def find_unresponsive(threshold):
    """Takes a threshold in minutes as an argument and prints
    all nodes that haven't submitted a report within threshold."""

    # First get a list of unique hosts
    node_list = get_node_list()
    # Get a list of unique hosts within the threshold
    recent_nodes = []
    query = {
        "size":0,
        "aggs": {
            "by_hosts": {
                "terms": {
                    "size": 0,
                    "field": "host"
                }
            }
        },
        "query" : {
            "range" : {
                "@timestamp": {
                    "gt": "now-{0}m".format(threshold)
                }
            }
        },
        "sort": [{"@timestamp":{"order":"desc"}}]
    }
    doc = search(query)
    logging.info("Returned {0} documents".format(doc['hits']['total']))
    document = doc['aggregations']['by_hosts']['buckets']
    for bucket in document:
        recent_nodes.append(bucket['key'])

    unresponsive_nodes = list(set(node_list) - set(recent_nodes))
    # Now gather last timestamp of nodes
    logging.info("Gathering last timestamp of unresponsive nodes")

    for node in unresponsive_nodes:
        query = {
            "size": 1,
            "query": {
                "match": {
                    "host": node
                }
            },
            "sort": [{"@timestamp":{"order":"desc"}}]
        }
        doc = search(query)
        logging.info("Returned {0} documents".format(doc['hits']['total']))
        timestamp = doc['hits']['hits'][0]['_source']['@timestamp']
        print "==== {0} exceeded threshold {1} minutes and last submitted report at {2} ====".format(node, threshold, timestamp)

def find_failed_catalogs():
    """ Prints a list of all nodes failing catalog compilation"""


    # First get a list of unique hosts
    node_list = get_node_list()
    failure_dict = {}
    environment = elastic_config.environment
    for node in node_list:
        query = {
            "size": 1,
            "query": {
                "filtered": {
                    "filter": {
                        "bool": {
                            "must": [
                                {
                                    "term": {"environment": environment}
                                },
                                {
                                    "term": {"host": node}
                                }
                            ]
                        }
                    }
                }
            },
            "sort": [{"@timestamp":{"order":"desc"}}]
        }
        doc = search(query)
        if doc['hits']['total'] > 0:
            logging.info("Returned {0} documents for {1}".format(doc['hits']['total'],node))
            document = doc['hits']['hits'][0]["_source"]
            indices = [i for i, line in enumerate(document["logs"]) if 'Could not retrieve catalog' in line]

            if indices:
                failure_message = document["logs"][indices[0]].split(" at ")[0]
                message_hash = hashlib.md5()
                message_hash.update(failure_message)
                hex_digest = message_hash.hexdigest()
                if failure_dict.has_key(hex_digest):
                    failure_dict[hex_digest][0] += 1
                    failure_dict[hex_digest][2].append("{0} on {1}".format(document["host"],document["@timestamp"]))
                else:
                    failure_dict[hex_digest] = [1,document["logs"][indices[0]],["{0} on {1}".format(document["host"],document["@timestamp"])]]

    if failure_dict:
        for k in failure_dict.keys():
            print "\n"+" "+"="*50
            print "{0}".format(failure_dict[k][1])
            print "COUNT: {0}".format(failure_dict[k][0])
            print "NODES AFFECTED:"
            for j in failure_dict[k][2]:
                print "{0}".format(j)
    else:
        sys.stdout.write("No catalog compilation failures!\n")

def main():
    args = parser.parse_args()
    global elastic_config
    elastic_config = common.LoadElasticConfig("puppet-show")
    pattern = elastic_config.index_pattern
    lookback = elastic_config.lookback
    indices = common.get_indexes(lookback, pattern)
    hosts = elastic_config.hosts
    port = elastic_config.port
    username = elastic_config.username
    password = elastic_config.password
    environment = elastic_config.environment
    if args.verbose:
        root = logging.getLogger()
        if root.handlers:
            for handler in root.handlers:
                root.removeHandler(handler)
        logging.basicConfig(level=logging.INFO)
    else:
         logging.basicConfig(level=logging.ERROR)
    if args.unresponsive:
        logging.info("Finding unresponsive nodes...")
        find_unresponsive(args.unresponsive)
    elif args.failures:
        logging.info("Finding nodes not compiling their catalog")
        find_failed_catalogs()


if __name__ == '__main__':
    main()

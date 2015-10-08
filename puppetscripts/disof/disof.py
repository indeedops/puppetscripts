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
from pyelasticsearch import ElasticSearch

try:
    from puppetscripts import common
except ImportError, ie:
    import common

urllib3.disable_warnings()

parser = argparse.ArgumentParser(description="This script is used to see if puppet runs succeeded or failed for a list of nodes from stdin")

parser.add_argument('--verbose',
                    action="store_const",
                    const=True,
                    dest="verbose",
                    help="Verbose mode.  Prints more information"
                    )

parser.add_argument('--summary',
                    action="store_const",
                    const=True,
                    dest="summary",
                    help="Only print the summary"
                    )

parser.add_argument('--only-failed',
                    action="store_const",
                    const=True,
                    dest="only_failed",
                    help="Only print failed nodes in summary"
                    )

parser.add_argument('--resource',
                    action="store",
                    dest="resource_title",
                    type=str,
                    help="Show status of a resource"
                    )

failed_nodes = {}


def process_results(result):
    try:
        doc = result[0]
        fqdn = result[1]
        if doc['hits']['total'] > 0:
            document = doc['hits']['hits'][0]
            timestamp = document['_source']['@timestamp']
            if args.resource_title:
                for resource in document['_source']['resource_statuses']:
                    if args.resource_title in resource['title']:
                        print "==== {0}[{1}] {2} on {3} at {4} ====".format(resource['resource_type'],resource['title'],resource['status'],fqdn, timestamp)
                        print "Message: {0} ".format(resource['message'])
            elif document['_source']['status'] == 'failed':
                print "==== {0} failed {1} ====".format(fqdn, timestamp)
                failed_nodes.update({fqdn:document['_source']['logs']})
            else:
                print "==== {0} succeeded {1} ====".format(fqdn, timestamp)
        else:
            print "==== No results for {0} in the past {1} days ====".format(fqdn, lookback)
    except:
        logging.error("Unexpected error processing results")
        pass

# Create tasks one per thing.
# Put tasks onto array
# have tasks write results to Queue
# go through array and wait for join
# write results

def search(elastic_config, fqdn):
    pattern = elastic_config.index_pattern
    lookback = elastic_config.lookback
    indices = common.get_indexes(lookback, pattern)
    hosts = elastic_config.hosts
    port = elastic_config.port
    username = elastic_config.username
    password = elastic_config.password
    environment = elastic_config.environment
    es = ElasticSearch(hosts, port=port, username=username, password=password)
    #try:
    doc = es.search(common.build_query(fqdn, environment), index=indices)
    return doc, fqdn
    #except:
    #    logging.error("Unexpected error searching for {0}. Passing".format(fqdn))
    #    pass

def main():
    elastic_config = common.LoadElasticConfig("disof")
    if args.verbose:
        root = logging.getLogger()
        if root.handlers:
            for handler in root.handlers:
                root.removeHandler(handler)
        logging.basicConfig(level=logging.INFO)
    else:
         logging.basicConfig(level=logging.ERROR)

    results = []
    jobs = []
    hosts = []
    pool_size = multiprocessing.cpu_count() * 2
    logging.info("Created pool of size {0}".format(pool_size))
    pool = multiprocessing.Pool(processes=pool_size)
    try:
        for i in sys.stdin:
            i = i.strip()
            pool.apply_async(search, args = (elastic_config, i, ), callback=process_results)
        pool.close()
        pool.join()
    except KeyboardInterrupt:
        logging.error("Caught Ctrl-c. Terminating")
        pool.terminate()
    except:
        logging.error("Unexpected error. Terminating.")
        pool.terminate()

    print "\nFailed Nodes:"
    for key, value in failed_nodes.iteritems():
        print "\t{0}:".format(key)
        if not args.summary:
            for i in value:
                print "\t\t{0}".format(i)
            print

if __name__ == '__main__':
    args = parser.parse_args()
    main()

# puppet-scripts

## Installation
```
git clone https://github.com/indeedops/puppetscripts.git
python puppet-scripts/setup.py install
```

## Configuration
Configuration can live in two locations (in order)
1. $HOME/.<application>.conf
1. /etc/puppet-scripts/<application>.conf

## Sample configuration
```
{
    "hosts":["https://elastic.example.com"],
    "port":443,
    "index_pattern":"%Y.%m.%d",
    "lookback":7
    "username":"admin"
    "password":"password1"
}
```

## Included programs
* puppet-disof
* puppet-show

### puppet-disof
Or: Did I Succeed Or Fail. A selection of nodes are sent through standard in and a summary of whether the runs succeeded or failed are sent back along with the logs of the failing nodes. The tool accepts three arguments:

* --verbose
* --summary: only print out the summary of the runs and no log output
* --resource: check if a particular resource failed
* --only-failed: Only print the failed nodes, not the successes

### puppet-show
The puppet-show script queries Elasticsearch. It can show different Puppet application failures or catalog compilation failures in the environment.

## config_version

We set a config version for our environments using a shell script specified in the environment.conf
```
config_version = /var/lib/puppet/bin/puppet_version.sh $environment /path/to/$environment/
manifest = /var/local/puppet-working-copies/$environment/manifests/site.pp
modulepath = /var/local/puppet-working-copies/$environment/modules:/var/local/puppet-working-copies/$environment/indeed/modules
```

### Usage

puppet_version.sh $environment /path/to/$environment

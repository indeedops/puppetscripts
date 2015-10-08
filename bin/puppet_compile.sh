#!/bin/sh

# puppet_compile.sh
# RVM users might need to set the proper PATH here
puppet master --compile $1 --hiera_conf /etc/puppet/hiera.yaml --confdir /etc/puppet --vardir /var/lib/puppet --environment "${ENVIRONMENT}" > /dev/null


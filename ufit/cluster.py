#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""
Utilities for clustering execution of a piece of code to multiple hosts using
SSH transport.
"""

import md5
import Queue
import StringIO
import threading
import cPickle as pickle
from os import path
from time import time

import paramiko

keyname = path.expanduser('~/.ufitcluster/key')
clusterlist = []

def init_cluster():
    fp = open(path.expanduser('~/.ufitcluster/hosts'))
    for line in fp: # user@host
        clusterlist.append(line.strip().split('@'))
    fp.close()


class ClusterError(Exception):
    pass


def job_runner(client, code, funcname, args, clientqueue, resultqueue, jobnum):
    try:
        sid = md5.new(str(time()) + str(args)).hexdigest()
        print '[C] starting job on', client._host
        code_footer = '''\nif __name__ == "__main__":
        import cPickle as pickle
        args = pickle.loads(%r)
        print pickle.dumps(%s(*args))
        ''' % (pickle.dumps(args), funcname)

        codeio = StringIO.StringIO(code + code_footer)
        sftp = client.open_sftp()
        sftp.putfo(codeio, '/tmp/ufit_cluster_%s.py' % sid)

        stdin, stdout, stderr = \
            client.exec_command('python /tmp/ufit_cluster_%s.py; '
                                     'rm /tmp/ufit_cluster_%s.py' % (sid, sid))
        try:
            result = pickle.load(stdout)
        except Exception:
            result = ClusterError(stderr.read())
        print '[C] done on %s: %r' % (client._host, result)
    except Exception, err:
        result = ClusterError(str(err))
    finally:
        resultqueue.put((jobnum, result))
        clientqueue.put(client)


def run_cluster(code, funcname, argumentslist):
    clients = []
    clientqueue = Queue.Queue()
    for i, (user, host) in enumerate(clusterlist):
        client = paramiko.SSHClient()
        client._host = '%s[%d]' % (host, i)
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, key_filename=keyname,
                       look_for_keys=False)
        clients.append(client)
        clientqueue.put(client)
    resultqueue = Queue.Queue()
    njobs = len(argumentslist)
    retval = [None] * njobs
    returns = 0
    for i, args in enumerate(argumentslist):
        client = clientqueue.get()
        threading.Thread(target=job_runner,
            args=(client, code, funcname, args, clientqueue, resultqueue, i)).start()
    while returns < njobs:
        jobnum, result = resultqueue.get()
        if isinstance(result, Exception):
            raise result
        retval[jobnum] = result
        returns += 1
    for cl in clients:
        cl.close()
    return retval

init_cluster()

if __name__ == '__main__':
    t1 = time()
    print run_cluster('def foo(a): return a\n', 'foo', [('a',),])
    t2 = time()
    print t2-t1

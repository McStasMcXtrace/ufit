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
from itertools import cycle

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

class Watcher(threading.Thread):
    def __init__(self, client, cid, queue, jobnum):
        self.client = client
        self.cid = cid
        self.queue = queue
        self.jobnum = jobnum
        threading.Thread.__init__(self)

    def run(self):
        print '[C] executing command on client', self.cid
        result = ClusterError('command execution failed')
        try:
            stdin, stdout, stderr = \
                self.client.exec_command('python /tmp/ufit_cluster_%s.py; '
                                         'rm /tmp/ufit_cluster_%s.py' % (self.cid, self.cid))
            try:
                result = pickle.load(stdout)
            except Exception:
                result = ClusterError(stderr.read())
            print '[C] done on client %s: %r' % (self.cid, result)
        finally:
            self.queue.put((self.jobnum, result))
            self.client.close()

def run_cluster(code, funcname, argumentslist):
    hosts = cycle(clusterlist)
    queue = Queue.Queue()
    njobs = len(argumentslist)
    retval = [None] * njobs
    returns = 0
    for i, args in enumerate(argumentslist):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        user, host = hosts.next()
        cid = md5.new(host + str(time()) + str(args)).hexdigest()
        print '[C] starting session on', host
        client.connect(host, username=user, key_filename=keyname,
                       look_for_keys=False)
        code_footer = '''\nif __name__ == "__main__":
        import cPickle as pickle
        args = pickle.loads(%r)
        print pickle.dumps(%s(*args))
        ''' % (pickle.dumps(args), funcname)
        codeio = StringIO.StringIO(code + code_footer)
        sftp = client.open_sftp()
        sftp.putfo(codeio, '/tmp/ufit_cluster_%s.py' % cid)
        Watcher(client, cid, queue, i).start()
    while returns < njobs:
        jobnum, result = queue.get()
        if isinstance(result, Exception):
            raise result
        retval[jobnum] = result
        returns += 1
    return retval

init_cluster()

if __name__ == '__main__':
    t1 = time()
    print run_cluster('def foo(a): return a\n', 'foo', [('a',),])
    t2 = time()
    print t2-t1

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


def client_runner(client, task_queue, result_queue, code, funcname):
    while True:
        jobnum, args = task_queue.get()
        if jobnum == -1:
            print '[C] exiting runner for %s' % client._host
            return
        try:
            sid = md5.new(str(time()) + str(args)).hexdigest()
            print '[C] starting session on %s, job %s' % (client._host, sid)
            code_footer = '''\nif __name__ == "__main__":
            import cPickle as pickle
            args = pickle.loads(%r)
            print pickle.dumps(%s(*args))
            ''' % (pickle.dumps(args), funcname)

            sftp = client.open_sftp()
            fobj = sftp.file('/tmp/ufit_cluster_%s.py' % sid, 'wb')
            fobj.write(code + code_footer)
            fobj.close()

            stdin, stdout, stderr = \
                client.exec_command('python /tmp/ufit_cluster_%s.py; '
                                    'rm /tmp/ufit_cluster_%s.py' % (sid, sid))
            result = pickle.load(stdout)
            print '[C] done on job %s: %r' % (sid, result)
            result_queue.put((jobnum, result))
        except Exception, err:
            print '[C] no result on %s, requeuing: %r' % (client._host, err)
            task_queue.put((jobnum, args))
            return


def run_cluster(code, funcname, argumentslist):
    clients = []
    runners = []
    task_queue = Queue.Queue()
    result_queue = Queue.Queue()
    for i, (user, host) in enumerate(clusterlist):
        client = paramiko.SSHClient()
        client._host = '%s[%d]' % (host, i)
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, key_filename=keyname,
                       look_for_keys=False)
        clients.append(client)
        runner = threading.Thread(target=client_runner,
            args=(client, task_queue, result_queue, code, funcname))
        runners.append(runner)
        runner.start()
    njobs = len(argumentslist)
    retval = [None] * njobs
    returns = 0
    for job in enumerate(argumentslist):
        task_queue.put(job)
    while returns < njobs:
        # XXX check if any client is still running
        jobnum, result = result_queue.get()
        if isinstance(result, Exception):
            raise result
        retval[jobnum] = result
        returns += 1
    for cl in clients:
        task_queue.put((-1, None))  # end!
        cl.close()
    return retval

init_cluster()

if __name__ == '__main__':
    t1 = time()
    print run_cluster('def foo(a): return a\n', 'foo', [('a',),])
    t2 = time()
    print t2-t1

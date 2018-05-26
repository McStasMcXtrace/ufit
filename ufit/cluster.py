#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""
Utilities for clustering execution of a piece of code to multiple hosts using
SSH transport.
"""

from __future__ import print_function

import sys
import md5
import threading
from os import path
from time import time

import paramiko

from ufit.pycompat import queue, cPickle as pickle

keyname = path.expanduser('~/.ufitcluster/key')
clusterlist = []


def init_cluster():
    try:
        fp = open(path.expanduser('~/.ufitcluster/hosts'))
        for line in fp:  # user@host
            if line.startswith('#'):
                continue
            login, host = line.strip().split('@')
            clusterlist.append((login, host))
        fp.close()
    except Exception as err:
        print('Cannot read the list of cluster hosts:', err, file=sys.stderr)
        print('Please create a file %s with one line for each '
              'parallel process, for example:' %
              path.expanduser('~/.ufitcluster/hosts'), file=sys.stderr)
        print(file=sys.stderr)
        print('username@hostname1', file=sys.stderr)
        print('username@hostname1', file=sys.stderr)
        print('username@hostname1', file=sys.stderr)
        print('username@hostname1', file=sys.stderr)
        print('username@hostname2', file=sys.stderr)
        print('username@hostname2', file=sys.stderr)
        print(file=sys.stderr)
        print('would run 4 parallel processes on hostname1 and '
              '2 parallel processes on hostname2.', file=sys.stderr)
        print('For local operation only, use "localhost" as '
              'hostname.', file=sys.stderr)
        print('The file %s must contain the SSH private key to '
              'use for the connection, even for localhost.' %
              path.expanduser('~/.ufitcluster/key'), file=sys.stderr)


def client_runner(client, task_queue, result_queue):
    while True:
        code, funcname, jobnum, args = task_queue.get()
        if jobnum == -1:
            print('[C] exiting runner for %s' % client._host)
            return
        try:
            sid = md5.new(str(time()) + str(args)).hexdigest()
            sys.stdout.write('.')
            sys.stdout.flush()
            # print '[C] starting job on %s: %s' % (client._host, sid)
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
            # print '[C] done with job %s: %r' % (sid, result)
            result_queue.put((jobnum, result))
        except Exception as err:
            print('[C] no result on %s, requeuing: %r' % (client._host, err))
            task_queue.put((code, funcname, jobnum, args))
            return


clients = []
runners = []
task_queue = queue.Queue()
result_queue = queue.Queue()
cluster_setup = False


def setup_cluster():
    global cluster_setup
    if cluster_setup:
        return
    for i, (user, host) in enumerate(clusterlist):
        client = paramiko.SSHClient()
        client._host = '%s[%d]' % (host, i)
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, key_filename=keyname,
                       look_for_keys=False)
        clients.append(client)
        print('[C] opened cluster connection to %s' % client._host)
        runner = threading.Thread(target=client_runner,
                                  args=(client, task_queue, result_queue))
        runners.append(runner)
        runner.start()
    cluster_setup = True


def kill_cluster():
    for cl in clients:
        task_queue.put((None, None, -1, None))  # end!
        cl.close()


def run_cluster(code, funcname, argumentslist):
    setup_cluster()
    njobs = len(argumentslist)
    retval = [None] * njobs
    returns = 0
    for job in enumerate(argumentslist):
        task_queue.put((code, funcname) + job)
    while returns < njobs:
        # XXX check if any client is still running
        jobnum, result = result_queue.get()
        if isinstance(result, Exception):
            raise result
        retval[jobnum] = result
        returns += 1
    return retval

init_cluster()

if __name__ == '__main__':
    t1 = time()
    print(run_cluster('def foo(a): return a\n', 'foo', [('a',)]))
    t2 = time()
    print(t2-t1)

#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2019, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

# Original author: Douglas Creager <dcreager@dcreager.net>
# This file is placed into the public domain.

import os.path
from subprocess import Popen, PIPE

__all__ = ['get_version']

RELEASE_VERSION_FILE = os.path.join(os.path.dirname(__file__),
                                    'RELEASE-VERSION')
GIT_REPO = os.path.join(os.path.dirname(__file__), '..', '.git')


def get_git_version(abbrev=4, cwd=None):
    try:
        p = Popen(['git', '--git-dir=%s' % GIT_REPO,
                   'describe', '--abbrev=%d' % abbrev],
                  stdout=PIPE, stderr=PIPE)
        stdout, _stderr = p.communicate()
        return stdout.strip().decode('utf-8', 'ignore')
    except Exception:
        return None


def read_release_version():
    try:
        with open(RELEASE_VERSION_FILE) as f:
            return f.readline().strip()
    except Exception:
        return None


def write_release_version(version):
    with open(RELEASE_VERSION_FILE, 'w') as f:
        f.write("%s\n" % version)


def get_version(abbrev=4):
    # determine the version from git and from RELEASE-VERSION
    git_version = get_git_version(abbrev)
    release_version = read_release_version()

    # if we have a git version, it is authoritative
    if git_version:
        if git_version != release_version:
            write_release_version(git_version)
        return git_version
    elif release_version:
        return release_version
    else:
        raise ValueError('Cannot find a version number - make sure that '
                         'git is installed or a RELEASE-VERSION file is '
                         'present!')


if __name__ == "__main__":
    print(get_version())

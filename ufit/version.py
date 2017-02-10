# -*- coding: utf-8 -*-
# Author: Douglas Creager <dcreager@dcreager.net>
# This file is placed into the public domain.

# Calculates the current version number.  If possible, this is the
# output of “git describe”, modified to conform to the versioning
# scheme that setuptools uses.  If “git describe” returns an error
# (most likely because we're in an unpacked copy of a release tarball,
# rather than in a git working copy), then we fall back on reading the
# contents of the RELEASE-VERSION file.
#
# To use this script, simply import it your setup.py file, and use the
# results of get_git_version() as your package version:
#
# from version import *
#
# setup(
#     version=get_git_version(),
#     .
#     .
#     .
# )
#
# This will automatically update the RELEASE-VERSION file, if
# necessary.  Note that the RELEASE-VERSION file should *not* be
# checked into git; please add it to your top-level .gitignore file.
#
# You'll probably want to distribute the RELEASE-VERSION file in your
# sdist tarballs; to do this, just create a MANIFEST.in file that
# contains the following line:
#
#   include RELEASE-VERSION

__all__ = ("get_git_version")

import os.path
from subprocess import Popen, PIPE

RELEASE_VERSION_FILE = os.path.join(os.path.dirname(__file__), 'RELEASE-VERSION')
GIT_REPO = os.path.join(os.path.dirname(__file__), '..', '.git')


def get_git_version(abbrev=4, cwd=None):
    try:
        p = Popen(['git', '--git-dir=%s' % GIT_REPO,
                   'describe', '--tags', '--abbrev=%d' % abbrev],
                  stdout=PIPE, stderr=PIPE)
        stdout, _stderr = p.communicate()
        return stdout.strip()
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
        raise ValueError('Cannot find a version number!')


if __name__ == "__main__":
    print(get_version())

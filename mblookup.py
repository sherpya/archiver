#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4 -*-
#
# Netfarm Mail Archiver - release 2
#
# Copyright (C) 2005-2007 Gianluigi Tiesi <sherpya@netfarm.it>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# ======================================================================
## @file mblookup.py
## Helper MailBox Lookup using postfix/cyrus

from types import ListType
from grp import getgrnam

__doc__ = '''Netfarm Archiver - release 2.1.0 - Postfix mailbox lookup'''
__version__ = '2.1.0'
__all__ = [ 'mblookup' ]

## Recurse in aliases
def lookup_alias(entry, db, bc):
    entries = entry[:-1].strip().split(',')
    results = []

    for entry in entries:
        key = entry.strip() + '\x00'
        value = db['aliases'].get(key)
        if value is not None:
            ## Loop detection
            if value in bc: return []
            bc.append(value)
            results = results + lookup_alias(value, db, bc)
        else:
            results = results + [entry.strip()]
    return results

## Lookup in virtual
def lookup(email, db):
    key = email.strip() + '\x00'
    value = db['virtual'].get(key)
    if value is None or value.find('@') != -1: return []
    bc = []
    return lookup_alias(value, db, bc)

def getusers(emails, dbfiles, postuser=None):
    if (type(emails) != ListType) or (len(emails) < 1): return []
    results = []
    res = []

    db = { 'virtual': dbfiles['virtual']['db'],
           'aliases': dbfiles['aliases']['db'] }

    for email in emails:
        res = res + lookup(email, db)

    # Uniq + Sort
    for mb in res:
        if mb in results: continue
        if mb.find('+') == -1:
            results.append(mb)
        else: ## Shared mailbox / direct folder post
            p, s = mb.split('+', 1)
            if postuser is not None and postuser == p:
                # postuser+group
                try:
                    results = results + getgrnam(s)[3] # TODO check for duplicates
                except: pass
            else: # user+folder
                mb = p
    results.sort()

    return results

if __name__ == '__main__':
    from anydbm import open as dbopen
    from sys import argv, exit as sys_exit

    if len(argv) < 2:
        print 'Usage %s: email [email email ...]' % argv[0]
        sys_exit(0)

    dbfiles = dict(virtual=dict(db={}), aliases=dict(db={}))

    # Virtual
    db = dbopen('/etc/postfix/virtual.db', 'r')
    dbfiles['virtual']['db'].update(db)
    db.close()

    # Aliases
    db = dbopen('/etc/postfix/aliases.db', 'r')
    dbfiles['aliases']['db'].update(db)
    db.close()

    postuser = None
    try:
        fd = open('/etc/imapd.conf', 'r')
        for line in fd:
            line = line.strip()
            if line.startswith('postuser:'):
                postuser = line.split(':', 1).pop().strip()
                break
    except:
        print 'Error reading postuser from imapd.conf'

    print getusers(argv[1:], dbfiles, postuser)

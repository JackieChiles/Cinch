#!/bin/env python
# -*- coding: utf-8 -*-

"""
### Edited to remove support for a lot of those databases that we'd never use,
### doctests, and some other stuff to trim down the module.
### Go find the original if you want it all.

| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
|

Thanks to

  - Niall Sweeny <niall.sweeny@fonjax.com> for MS SQL support
  - Marcel Leuthi <mluethi@mlsystems.ch> for Oracle support
  - Denes
  - Chris Clark
  - clach05
  - Denes Lengyel

and many others who have contributed to current and previous versions

<snip>

For more info::

    help(DAL)
    help(Field)

"""

###################################################################################
# this file only exposes DAL and Field
###################################################################################

__all__ = ['DAL', 'Field']

DEFAULTLENGTH = {'string':512,
                 'password':512,
                 'upload':512,
                 'text':2**15,
                 'blob':2**31}
TIMINGSSIZE = 100
SPATIALLIBS = {'Windows':'libspatialite',
               'Linux':'libspatialite.so',
               'Darwin':'libspatialite.dylib'
               }
DEFAULT_URI = 'sqlite://dummy.db'

import re
import sys
import locale
import os
import types
import datetime
import threading
import time
import csv
import cgi
import copy
import socket
import logging
import base64
import shutil
import marshal
import decimal
import struct
import urllib
import hashlib
import uuid
import glob
import traceback
import platform

PYTHON_VERSION = sys.version_info[:3]
if PYTHON_VERSION[0] == 2:
    import cPickle as pickle
    import cStringIO as StringIO
    import copy_reg as copyreg
    hashlib_md5 = hashlib.md5
    bytes, unicode = str, unicode
else:
    import pickle
    from io import StringIO as StringIO
    import copyreg
    long = int
    hashlib_md5 = lambda s: hashlib.md5(bytes(s, 'utf8'))
    bytes, unicode = bytes, str

if PYTHON_VERSION[:2] < (2, 7):
    from gluon.contrib.ordereddict import OrderedDict
else:
    from collections import OrderedDict


CALLABLETYPES = (types.LambdaType, types.FunctionType,
                 types.BuiltinFunctionType,
                 types.MethodType, types.BuiltinMethodType)

TABLE_ARGS = set(('migrate', 'primarykey', 'fake_migrate', 'format', 'redefine',
                  'singular', 'plural', 'trigger_name', 'sequence_name', 'fields',
                  'common_filter', 'polymodel', 'table_class', 'on_define', 'rname'))

SELECT_ARGS = set(('orderby', 'groupby', 'limitby', 'required', 'cache', 'left',
                   'distinct', 'having', 'join', 'for_update', 'processor',
                   'cacheable', 'orderby_on_limitby'))

ogetattr = object.__getattribute__
osetattr = object.__setattr__
exists = os.path.exists
pjoin = os.path.join

###################################################################################
# following checks allow the use of dal without web2py, as a standalone module
###################################################################################
try:
    from gluon.utils import web2py_uuid
except (ImportError, SystemError):
    import uuid

    def web2py_uuid(): return str(uuid.uuid4())

try:
    import portalocker
    have_portalocker = True
except ImportError:
    have_portalocker = False

try:
    from gluon import serializers
    have_serializers = True
except ImportError:
    have_serializers = False
    try:
        import json as simplejson
    except ImportError:
        try:
            import gluon.contrib.simplejson as simplejson
        except ImportError:
            simplejson = None

LOGGER = logging.getLogger("web2py.dal")
DEFAULT = lambda: 0

GLOBAL_LOCKER = threading.RLock()
THREAD_LOCAL = threading.local()

# internal representation of tables with field
#  <table>.<field>, tables and fields may only be [a-zA-Z0-9_]

REGEX_TYPE = re.compile('^([\w\_\:]+)')
REGEX_DBNAME = re.compile('^(\w+)(\:\w+)*')
REGEX_W = re.compile('^\w+$')
REGEX_TABLE_DOT_FIELD = re.compile('^(\w+)\.([^.]+)$')
REGEX_NO_GREEDY_ENTITY_NAME = r'(.+?)'
REGEX_UPLOAD_PATTERN = re.compile('(?P<table>[\w\-]+)\.(?P<field>[\w\-]+)\.(?P<uuidkey>[\w\-]+)(\.(?P<name>\w+))?\.\w+$')
REGEX_CLEANUP_FN = re.compile('[\'"\s;]+')
REGEX_UNPACK = re.compile('(?<!\|)\|(?!\|)')
REGEX_PYTHON_KEYWORDS = re.compile('^(and|del|from|not|while|as|elif|global|or|with|assert|else|if|pass|yield|break|except|import|print|class|exec|in|raise|continue|finally|is|return|def|for|lambda|try)$')
REGEX_SELECT_AS_PARSER = re.compile("\s+AS\s+(\S+)")
REGEX_CONST_STRING = re.compile('(\"[^\"]*?\")|(\'[^\']*?\')')
REGEX_SEARCH_PATTERN = re.compile('^{[^\.]+\.[^\.]+(\.(lt|gt|le|ge|eq|ne|contains|startswith|year|month|day|hour|minute|second))?(\.not)?}$')
REGEX_SQUARE_BRACKETS = re.compile('^.+\[.+\]$')
REGEX_STORE_PATTERN = re.compile('\.(?P<e>\w{1,5})$')
REGEX_QUOTES = re.compile("'[^']*'")
REGEX_ALPHANUMERIC = re.compile('^[0-9a-zA-Z]\w*$')
REGEX_PASSWORD = re.compile('\://([^:@]*)\:')
REGEX_NOPASSWD = re.compile('\/\/[\w\.\-]+[\:\/](.+)(?=@)') # was '(?<=[\:\/])([^:@/]+)(?=@.+)'

# list of drivers will be built on the fly
# and lists only what is available
DRIVERS = []

try:
    from new import classobj
except ImportError:
    pass

if not 'google' in DRIVERS:

    try:
        from pysqlite2 import dbapi2 as sqlite2
        DRIVERS.append('SQLite(sqlite2)')
    except ImportError:
        LOGGER.debug('no SQLite drivers pysqlite2.dbapi2')

    try:
        from sqlite3 import dbapi2 as sqlite3
        DRIVERS.append('SQLite(sqlite3)')
    except ImportError:
        LOGGER.debug('no SQLite drivers sqlite3')

    try:
        # first try contrib driver, then from site-packages (if installed)
        try:
            import gluon.contrib.pymysql as pymysql
            # monkeypatch pymysql because they havent fixed the bug:
            # https://github.com/petehunt/PyMySQL/issues/86
            pymysql.ESCAPE_REGEX = re.compile("'")
            pymysql.ESCAPE_MAP = {"'": "''"}
            # end monkeypatch
        except ImportError:
            import pymysql
        DRIVERS.append('MySQL(pymysql)')
    except ImportError:
        LOGGER.debug('no MySQL driver pymysql')

    try:
        import MySQLdb
        DRIVERS.append('MySQL(MySQLdb)')
    except ImportError:
        LOGGER.debug('no MySQL driver MySQLDB')

    try:
        import mysql.connector as mysqlconnector
        DRIVERS.append("MySQL(mysqlconnector)")
    except ImportError:
        LOGGER.debug("no driver mysql.connector")


PLURALIZE_RULES = [(re.compile('child$'), re.compile('child$'), 'children'),
                   (re.compile('oot$'), re.compile('oot$'), 'eet'),
                   (re.compile('ooth$'), re.compile('ooth$'), 'eeth'),
                   (re.compile('l[eo]af$'), re.compile('l([eo])af$'), 'l\\1aves'),
                   (re.compile('sis$'), re.compile('sis$'), 'ses'),
                   (re.compile('man$'), re.compile('man$'), 'men'),
                   (re.compile('ife$'), re.compile('ife$'), 'ives'),
                   (re.compile('eau$'), re.compile('eau$'), 'eaux'),
                   (re.compile('lf$'), re.compile('lf$'), 'lves'),
                   (re.compile('[sxz]$'), re.compile('$'), 'es'),
                   (re.compile('[^aeioudgkprt]h$'), re.compile('$'), 'es'),
                   (re.compile('(qu|[^aeiou])y$'), re.compile('y$'), 'ies'),
                   (re.compile('$'), re.compile('$'), 's'),
                   ]


def pluralize(singular, rules=PLURALIZE_RULES):
    for line in rules:
        re_search, re_sub, replace = line
        plural = re_search.search(singular) and re_sub.sub(replace, singular)
        if plural: return plural


def hide_password(uri):
    if isinstance(uri, (list, tuple)):
        return [hide_password(item) for item in uri]
    return REGEX_NOPASSWD.sub('******', uri)


def OR(a, b):
    return a|b


def AND(a, b):
    return a&b


def IDENTITY(x): return x


def varquote_aux(name, quotestr='%s'):
    return name if REGEX_W.match(name) else quotestr % name


def quote_keyword(a, keyword='timestamp'):
    regex = re.compile('\.keyword(?=\w)')
    a = regex.sub('."%s"' % keyword, a)
    return a


###################################################################################
# class that handles connection pooling (all adapters are derived from this one)
###################################################################################

class ConnectionPool(object):

    POOLS = {}
    check_active_connection = True

    @staticmethod
    def set_folder(folder):
        THREAD_LOCAL.folder = folder

    # ## this allows gluon to commit/rollback all dbs in this thread

    def close(self, action='commit', really=True):
        if action:
            if callable(action):
                action(self)
            else:
                getattr(self, action)()
        # ## if you want pools, recycle this connection
        if self.pool_size:
            GLOBAL_LOCKER.acquire()
            pool = ConnectionPool.POOLS[self.uri]
            if len(pool) < self.pool_size:
                pool.append(self.connection)
                really = False
            GLOBAL_LOCKER.release()
        if really:
            self.close_connection()
        self.connection = None

    @staticmethod
    def close_all_instances(action):
        """ to close cleanly databases in a multithreaded environment """
        dbs = getattr(THREAD_LOCAL, 'db_instances', {}).items()
        for db_uid, db_group in dbs:
            for db in db_group:
                if hasattr(db, '_adapter'):
                    db._adapter.close(action)
        getattr(THREAD_LOCAL, 'db_instances', {}).clear()
        getattr(THREAD_LOCAL, 'db_instances_zombie', {}).clear()
        if callable(action):
            action(None)
        return

    def find_or_make_work_folder(self):
        #this actually does not make the folder. it has to be there
        self.folder = getattr(THREAD_LOCAL, 'folder', '')

        if (os.path.isabs(self.folder) and
            isinstance(self, UseDatabaseStoredFile) and
            self.folder.startswith(os.getcwd())):
            self.folder = os.path.relpath(self.folder, os.getcwd())

        # Creating the folder if it does not exist
        if False and self.folder and not exists(self.folder):
            os.mkdir(self.folder)

    def after_connection_hook(self):
        """Hook for the after_connection parameter"""
        if callable(self._after_connection):
            self._after_connection(self)
        self.after_connection()

    def after_connection(self):
        #this it is supposed to be overloaded by adapters
        pass

    def reconnect(self, f=None, cursor=True):
        """
        Defines: `self.connection` and `self.cursor`
        (if cursor is True)
        if `self.pool_size>0` it will try pull the connection from the pool
        if the connection is not active (closed by db server) it will loop
        if not `self.pool_size` or no active connections in pool makes a new one
        """
        if getattr(self, 'connection', None) is not None:
            return
        if f is None:
            f = self.connector

        # if not hasattr(self, "driver") or self.driver is None:
        #     LOGGER.debug("Skipping connection since there's no driver")
        #     return

        if not self.pool_size:
            self.connection = f()
            self.cursor = cursor and self.connection.cursor()
        else:
            uri = self.uri
            POOLS = ConnectionPool.POOLS
            while True:
                GLOBAL_LOCKER.acquire()
                if not uri in POOLS:
                    POOLS[uri] = []
                if POOLS[uri]:
                    self.connection = POOLS[uri].pop()
                    GLOBAL_LOCKER.release()
                    self.cursor = cursor and self.connection.cursor()
                    try:
                        if self.cursor and self.check_active_connection:
                            self.execute('SELECT 1;')
                        break
                    except:
                        pass
                else:
                    GLOBAL_LOCKER.release()
                    self.connection = f()
                    self.cursor = cursor and self.connection.cursor()
                    break
        self.after_connection_hook()


###################################################################################
# metaclass to prepare adapter classes static values
###################################################################################
class AdapterMeta(type):
    """Metaclass to support manipulation of adapter classes.

    At the moment is used to intercept `entity_quoting` argument passed to DAL.
    """

    def __call__(cls, *args, **kwargs):
        entity_quoting = kwargs.get('entity_quoting', False)
        if 'entity_quoting' in kwargs:
             del kwargs['entity_quoting']

        obj = super(AdapterMeta, cls).__call__(*args, **kwargs)
        if not entity_quoting:
            quot = obj.QUOTE_TEMPLATE = '%s'
            regex_ent = r'(\w+)'
        else:
            quot = obj.QUOTE_TEMPLATE
            regex_ent = REGEX_NO_GREEDY_ENTITY_NAME
        obj.REGEX_TABLE_DOT_FIELD = re.compile(r'^' + \
                                                    quot % regex_ent + \
                                                    r'\.' + \
                                                    quot % regex_ent + \
                                                    r'$')

        return obj


###############################################################################
# this is a generic adapter that does nothing; all others are derived from this
###############################################################################
class BaseAdapter(ConnectionPool):

    __metaclass__ = AdapterMeta

    native_json = False
    driver = None
    driver_name = None
    drivers = ()  # list of drivers from which to pick
    connection = None
    commit_on_alter_table = False
    support_distributed_transaction = False
    uploads_in_blob = False
    can_select_for_update = True
    dbpath = None
    folder = None
    connector = lambda *args, **kwargs: None  # __init__ should override this

    TRUE = 'T'
    FALSE = 'F'
    T_SEP = ' '
    QUOTE_TEMPLATE = '"%s"'

    types = {'boolean': 'CHAR(1)',
             'string': 'CHAR(%(length)s)',
             'text': 'TEXT',
             'json': 'TEXT',
             'password': 'CHAR(%(length)s)',
             'blob': 'BLOB',
             'upload': 'CHAR(%(length)s)',
             'integer': 'INTEGER',
             'bigint': 'INTEGER',
             'float': 'DOUBLE',
             'double': 'DOUBLE',
             'decimal': 'DOUBLE',
             'date': 'DATE',
             'time': 'TIME',
             'datetime': 'TIMESTAMP',
             'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
             'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
             'list:integer': 'TEXT',
             'list:string': 'TEXT',
             'list:reference': 'TEXT',
             # the two below are only used when DAL(...bigint_id=True) and replace 'id','reference'
             'big-id': 'BIGINT PRIMARY KEY AUTOINCREMENT',
             'big-reference': 'BIGINT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
             'reference FK': ', CONSTRAINT  "FK_%(constraint_name)s" FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
             }

    def isOperationalError(self, exception):
        if not hasattr(self.driver, "OperationalError"):
            return None
        return isinstance(exception, self.driver.OperationalError)

    def isProgrammingError(self, exception):
        if not hasattr(self.driver, "ProgrammingError"):
            return None
        return isinstance(exception, self.driver.ProgrammingError)

    def id_query(self, table):
        pkeys = getattr(table, '_primarykey', None)
        if pkeys:
            return table[pkeys[0]] != None
        else:
            return table._id != None

    def adapt(self, obj):
        return "'%s'" % obj.replace("'", "''")

    def smart_adapt(self, obj):
        if isinstance(obj, (int, float)):
            return str(obj)
        return self.adapt(str(obj))

    def file_exists(self, filename):
        # to be used ONLY for files that on GAE may not be on filesystem
        return exists(filename)

    def file_open(self, filename, mode='rb', lock=True):
        # to be used ONLY for files that on GAE may not be on filesystem
        if have_portalocker and lock:
            fileobj = portalocker.LockedFile(filename, mode)
        else:
            fileobj = open(filename, mode)
        return fileobj

    def file_close(self, fileobj):
        #to be used ONLY for files that on GAE may not be on filesystem
        if fileobj:
            fileobj.close()

    def file_delete(self, filename):
        os.unlink(filename)

    def find_driver(self, adapter_args, uri=None):
        self.adapter_args = adapter_args
        if getattr(self, 'driver', None) != None:
            return
        drivers_available = [driver for driver in self.drivers
                             if driver in globals()]
        if uri:
            items = uri.split('://', 1)[0].split(':')
            request_driver = items[1] if len(items) > 1 else None
        else:
            request_driver = None
        request_driver = request_driver or adapter_args.get('driver')
        if request_driver:
            if request_driver in drivers_available:
                self.driver_name = request_driver
                self.driver = globals().get(request_driver)
            else:
                raise RuntimeError("driver %s not available" % request_driver)
        elif drivers_available:
            self.driver_name = drivers_available[0]
            self.driver = globals().get(self.driver_name)
        else:
            raise RuntimeError("no driver available %s" % str(self.drivers))

    def log(self, message, table=None):
        """ Logs migrations

        It will not log changes if logfile is not specified. Defaults
        to sql.log
        """

        isabs = None
        logfilename = self.adapter_args.get('logfile', 'sql.log')
        writelog = bool(logfilename)
        if writelog:
            isabs = os.path.isabs(logfilename)

        if table and table._dbt and writelog and self.folder:
            if isabs:
                table._loggername = logfilename
            else:
                table._loggername = pjoin(self.folder, logfilename)
            logfile = self.file_open(table._loggername, 'a')
            logfile.write(message)
            self.file_close(logfile)

    def __init__(self, db, uri, pool_size=0, folder=None, db_codec='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "None"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection

        class Dummy(object):
            lastrowid = 1

            def __getattr__(self, value):
                return lambda *a, **b: []
        self.connection = Dummy()
        self.cursor = Dummy()

    def sequence_name(self, tablename):
        return self.QUOTE_TEMPLATE % ('%s_sequence' % tablename)

    def trigger_name(self, tablename):
        return '%s_sequence' % tablename

    def varquote(self, name):
        return name

    def create_table(self, table,
                     migrate=True,
                     fake_migrate=False,
                     polymodel=None):
        db = table._db
        fields = []
        # PostGIS geo fields are added after the table has been created
        postcreation_fields = []
        sql_fields = {}
        sql_fields_aux = {}
        TFK = {}
        tablename = table._tablename
        sortable = 0
        types = self.types
        for field in table:
            sortable += 1
            field_name = field.name
            field_type = field.type
            if isinstance(field_type, SQLCustomType):
                ftype = field_type.native or field_type.type
            elif field_type.startswith('reference'):
                referenced = field_type[10:].strip()
                if referenced == '.':
                    referenced = tablename
                constraint_name = self.constraint_name(tablename, field_name)
                # if not '.' in referenced \
                #         and referenced != tablename \
                #         and hasattr(table, '_primarykey'):
                #     ftype = types['integer']
                # else:
                try:
                    rtable = db[referenced]
                    rfield = rtable._id
                    rfieldname = rfield.name
                    rtablename = referenced
                except (KeyError, ValueError, AttributeError), e:
                    LOGGER.debug('Error: %s' % e)
                    try:
                        rtablename, rfieldname = referenced.split('.')
                        rtable = db[rtablename]
                        rfield = rtable[rfieldname]
                    except Exception, e:
                        LOGGER.debug('Error: %s' %e)
                        raise KeyError('Cannot resolve reference %s in %s definition' % (referenced, table._tablename))

                # must be PK reference or unique
                if getattr(rtable, '_primarykey', None) and rfieldname in rtable._primarykey or \
                        rfield.unique:
                    ftype = types[rfield.type[:9]] % \
                        dict(length=rfield.length)
                    # multicolumn primary key reference?
                    if not rfield.unique and len(rtable._primarykey)>1:
                        # then it has to be a table level FK
                        if rtablename not in TFK:
                            TFK[rtablename] = {}
                        TFK[rtablename][rfieldname] = field_name
                    else:
                        ftype = ftype + \
                            types['reference FK'] % dict(
                                constraint_name = constraint_name,  # should be quoted
                                foreign_key = rtable.sqlsafe + ' (' + rfield.sqlsafe_name + ')',
                                table_name = table.sqlsafe,
                                field_name = field.sqlsafe_name,
                                on_delete_action=field.ondelete)
                else:
                    # make a guess here for circular references
                    if referenced in db:
                        id_fieldname = db[referenced]._id.sqlsafe_name
                    elif referenced == tablename:
                        id_fieldname = table._id.sqlsafe_name
                    else: #make a guess
                        id_fieldname = self.QUOTE_TEMPLATE % 'id'
                    # gotcha: the referenced table must be defined before
                    # the referencing one to be able to create the table
                    # Also if it's not recommended, we can still support
                    # references to tablenames without rname to make
                    # migrations and model relationship work also if tables
                    # are not defined in order
                    if referenced == tablename:
                        real_referenced = db[referenced].sqlsafe
                    else:
                        real_referenced = (referenced in db
                                           and db[referenced].sqlsafe
                                           or referenced)
                    rfield = db[referenced]._id
                    ftype = types[field_type[:9]] % dict(
                        index_name=self.QUOTE_TEMPLATE % (field_name+'__idx'),
                        field_name=field.sqlsafe_name,
                        constraint_name=self.QUOTE_TEMPLATE % constraint_name,
                        foreign_key='%s (%s)' % (real_referenced, rfield.sqlsafe_name),
                        on_delete_action=field.ondelete)
            elif field_type.startswith('list:reference'):
                ftype = types[field_type[:14]]
            elif field_type.startswith('decimal'):
                precision, scale = map(int, field_type[8:-1].split(','))
                ftype = types[field_type[:7]] % \
                    dict(precision=precision, scale=scale)
            elif field_type.startswith('geo'):
                if not hasattr(self, 'srid'):
                    raise RuntimeError('Adapter does not support geometry')
                srid = self.srid
                geotype, parms = field_type[:-1].split('(')
                if not geotype in types:
                    raise SyntaxError('Field: unknown field type: %s for %s'
                                      % (field_type, field_name))
                ftype = types[geotype]
                if self.dbengine == 'postgres' and geotype == 'geometry':
                    # parameters: schema, srid, dimension
                    dimension = 2  # GIS.dimension ???
                    parms = parms.split(',')
                    if len(parms) == 3:
                        schema, srid, dimension = parms
                    elif len(parms) == 2:
                        schema, srid = parms
                    else:
                        schema = parms[0]
                    ftype = "SELECT AddGeometryColumn ('%%(schema)s', '%%(tablename)s', '%%(fieldname)s', %%(srid)s, '%s', %%(dimension)s);" % types[geotype]
                    ftype = ftype % dict(schema=schema,
                                         tablename=tablename,
                                         fieldname=field_name, srid=srid,
                                         dimension=dimension)
                    postcreation_fields.append(ftype)
            elif not field_type in types:
                raise SyntaxError('Field: unknown field type: %s for %s'
                                  % (field_type, field_name))
            else:
                ftype = types[field_type]\
                     % dict(length=field.length)
            if not field_type.startswith('id') and \
                    not field_type.startswith('reference'):
                if field.notnull:
                    ftype += ' NOT NULL'
                else:
                    ftype += self.ALLOW_NULL()
                if field.unique:
                    ftype += ' UNIQUE'
                if field.custom_qualifier:
                    ftype += ' %s' % field.custom_qualifier

            # add to list of fields
            sql_fields[field_name] = dict(
                length=field.length,
                unique=field.unique,
                notnull=field.notnull,
                sortable=sortable,
                type=str(field_type),
                sql=ftype)

            if field.notnull and not field.default is None:
                # Caveat: sql_fields and sql_fields_aux
                # differ for default values.
                # sql_fields is used to trigger migrations and sql_fields_aux
                # is used for create tables.
                # The reason is that we do not want to trigger
                # a migration simply because a default value changes.
                not_null = self.NOT_NULL(field.default, field_type)
                ftype = ftype.replace('NOT NULL', not_null)
            sql_fields_aux[field_name] = dict(sql=ftype)
            # Postgres - PostGIS:
            # geometry fields are added after the table has been created, not now
            if not (self.dbengine == 'postgres'
                    and field_type.startswith('geom')):
                fields.append('%s %s' % (field.sqlsafe_name, ftype))
        other = ';'

        # backend-specific extensions to fields
        if self.dbengine == 'mysql':
            if not hasattr(table, "_primarykey"):
                fields.append('PRIMARY KEY (%s)' % (self.QUOTE_TEMPLATE % table._id.name))
            engine = self.adapter_args.get('engine', 'InnoDB')
            other = ' ENGINE=%s CHARACTER SET utf8;' % engine

        fields = ',\n    '.join(fields)
        for rtablename in TFK:
            rfields = TFK[rtablename]
            pkeys = [self.QUOTE_TEMPLATE % pk for pk in db[rtablename]._primarykey]
            fkeys = [self.QUOTE_TEMPLATE % rfields[k].name for k in pkeys]
            fields = fields + ',\n    ' + \
                types['reference TFK'] % dict(
                table_name = table.sqlsafe,
                field_name=', '.join(fkeys),
                foreign_table = table.sqlsafe,
                foreign_key = ', '.join(pkeys),
                on_delete_action = field.ondelete)

        table_rname = table.sqlsafe

        if getattr(table, '_primarykey', None):
            query = "CREATE TABLE %s(\n    %s,\n    %s) %s" % \
                (table.sqlsafe, fields,
                 self.PRIMARY_KEY(', '.join([self.QUOTE_TEMPLATE % pk for pk in table._primarykey])), other)
        else:
            query = "CREATE TABLE %s(\n    %s\n)%s" % \
                (table.sqlsafe, fields, other)

        if self.uri.startswith('sqlite:///') \
                or self.uri.startswith('spatialite:///'):
            path_encoding = sys.getfilesystemencoding() \
                or locale.getdefaultlocale()[1] or 'utf8'
            dbpath = self.uri[9:self.uri.rfind('/')]\
                .decode('utf8').encode(path_encoding)
        else:
            dbpath = self.folder

        if not migrate:
            return query
        elif self.uri.startswith('sqlite:memory')\
                or self.uri.startswith('spatialite:memory'):
            table._dbt = None
        elif isinstance(migrate, str):
            table._dbt = pjoin(dbpath, migrate)
        else:
            table._dbt = pjoin(
                dbpath, '%s_%s.table' % (table._db._uri_hash, tablename))

        if not table._dbt or not self.file_exists(table._dbt):
            if table._dbt:
                self.log('timestamp: %s\n%s\n'
                         % (datetime.datetime.today().isoformat(),
                            query), table)
            if not fake_migrate:
                self.create_sequence_and_triggers(query, table)
                table._db.commit()
                # Postgres geom fields are added now,
                # after the table has been created
                for query in postcreation_fields:
                    self.execute(query)
                    table._db.commit()
            if table._dbt:
                tfile = self.file_open(table._dbt, 'w')
                pickle.dump(sql_fields, tfile)
                self.file_close(tfile)
                if fake_migrate:
                    self.log('faked!\n', table)
                else:
                    self.log('success!\n', table)
        else:
            tfile = self.file_open(table._dbt, 'r')
            try:
                sql_fields_old = pickle.load(tfile)
            except EOFError:
                self.file_close(tfile)
                raise RuntimeError('File %s appears corrupted' % table._dbt)
            self.file_close(tfile)
            if sql_fields != sql_fields_old:
                self.migrate_table(table,
                                   sql_fields, sql_fields_old,
                                   sql_fields_aux, None,
                                   fake_migrate=fake_migrate
                                   )
        return query

    def migrate_table(self,
                      table,
                      sql_fields,
                      sql_fields_old,
                      sql_fields_aux,
                      logfile,
                      fake_migrate=False,
                      ):

        # logfile is deprecated (moved to adapter.log method)
        db = table._db
        db._migrated.append(table._tablename)
        tablename = table._tablename

        def fix(item):
            k, v = item
            if not isinstance(v, dict):
                v = dict(type='unknown', sql=v)
            if self.ignore_field_case is not True: return k, v
            return k.lower(), v
        # make sure all field names are lower case to avoid
        # migrations because of case cahnge
        sql_fields = dict(map(fix, sql_fields.iteritems()))
        sql_fields_old = dict(map(fix, sql_fields_old.iteritems()))
        sql_fields_aux = dict(map(fix, sql_fields_aux.iteritems()))
        if db._debug:
            logging.debug('migrating %s to %s' % (sql_fields_old, sql_fields))

        keys = sql_fields.keys()
        for key in sql_fields_old:
            if not key in keys:
                keys.append(key)
        new_add = self.concat_add(tablename)

        metadata_change = False
        sql_fields_current = copy.copy(sql_fields_old)
        for key in keys:
            query = None
            if not key in sql_fields_old:
                sql_fields_current[key] = sql_fields[key]
                if self.dbengine in ('postgres',) and \
                   sql_fields[key]['type'].startswith('geometry'):
                    # 'sql' == ftype in sql
                    query = [sql_fields[key]['sql']]
                else:
                    query = ['ALTER TABLE %s ADD %s %s;' % (table.sqlsafe, key,
                             sql_fields_aux[key]['sql'].replace(', ', new_add))]
                metadata_change = True
            elif self.dbengine in ('sqlite', 'spatialite'):
                if key in sql_fields:
                    sql_fields_current[key] = sql_fields[key]
                metadata_change = True
            elif not key in sql_fields:
                del sql_fields_current[key]
                ftype = sql_fields_old[key]['type']
                if (self.dbengine in ('postgres',) and
                    ftype.startswith('geometry')):
                    geotype, parms = ftype[:-1].split('(')
                    schema = parms.split(',')[0]
                    query = ["SELECT DropGeometryColumn ('%(schema)s', "+
                              "'%(table)s', '%(field)s');" %
                              dict(schema=schema, table=tablename, field=key)]
                elif self.dbengine in ('firebird',):
                    query = ['ALTER TABLE %s DROP %s;' %
                             (self.QUOTE_TEMPLATE % tablename, self.QUOTE_TEMPLATE % key)]
                else:
                    query = ['ALTER TABLE %s DROP COLUMN %s;' %
                             (self.QUOTE_TEMPLATE % tablename, self.QUOTE_TEMPLATE % key)]
                metadata_change = True
            elif sql_fields[key]['sql'] != sql_fields_old[key]['sql'] \
                  and not (key in table.fields and
                           isinstance(table[key].type, SQLCustomType)) \
                  and not sql_fields[key]['type'].startswith('reference')\
                  and not sql_fields[key]['type'].startswith('double')\
                  and not sql_fields[key]['type'].startswith('id'):
                sql_fields_current[key] = sql_fields[key]
                t = tablename
                tt = sql_fields_aux[key]['sql'].replace(', ', new_add)
                if self.dbengine in ('firebird',):
                    drop_expr = 'ALTER TABLE %s DROP %s;'
                else:
                    drop_expr = 'ALTER TABLE %s DROP COLUMN %s;'
                key_tmp = key + '__tmp'
                query = ['ALTER TABLE %s ADD %s %s;' % (self.QUOTE_TEMPLATE % t, self.QUOTE_TEMPLATE % key_tmp, tt),
                         'UPDATE %s SET %s=%s;' %
                         (self.QUOTE_TEMPLATE % t, self.QUOTE_TEMPLATE % key_tmp, self.QUOTE_TEMPLATE % key),
                         drop_expr % (self.QUOTE_TEMPLATE % t, self.QUOTE_TEMPLATE % key),
                         'ALTER TABLE %s ADD %s %s;' %
                         (self.QUOTE_TEMPLATE % t, self.QUOTE_TEMPLATE % key, tt),
                         'UPDATE %s SET %s=%s;' %
                         (self.QUOTE_TEMPLATE % t, self.QUOTE_TEMPLATE % key, self.QUOTE_TEMPLATE % key_tmp),
                         drop_expr % (self.QUOTE_TEMPLATE % t, self.QUOTE_TEMPLATE % key_tmp)]
                metadata_change = True
            elif sql_fields[key]['type'] != sql_fields_old[key]['type']:
                sql_fields_current[key] = sql_fields[key]
                metadata_change = True

            if query:
                self.log('timestamp: %s\n'
                    % datetime.datetime.today().isoformat(), table)
                db['_lastsql'] = '\n'.join(query)
                for sub_query in query:
                    self.log(sub_query + '\n', table)
                    if fake_migrate:
                        if db._adapter.commit_on_alter_table:
                            self.save_dbt(table, sql_fields_current)
                        self.log('faked!\n', table)
                    else:
                        self.execute(sub_query)
                        # Caveat: mysql, oracle and firebird
                        # do not allow multiple alter table
                        # in one transaction so we must commit
                        # partial transactions and
                        # update table._dbt after alter table.
                        if db._adapter.commit_on_alter_table:
                            db.commit()
                            self.save_dbt(table, sql_fields_current)
                            self.log('success!\n', table)

            elif metadata_change:
                self.save_dbt(table, sql_fields_current)

        if metadata_change and not (query and db._adapter.commit_on_alter_table):
            db.commit()
            self.save_dbt(table, sql_fields_current)
            self.log('success!\n', table)

    def save_dbt(self, table, sql_fields_current):
        tfile = self.file_open(table._dbt, 'w')
        pickle.dump(sql_fields_current, tfile)
        self.file_close(tfile)

    def LOWER(self, first):
        return 'LOWER(%s)' % self.expand(first)

    def UPPER(self, first):
        return 'UPPER(%s)' % self.expand(first)

    def COUNT(self, first, distinct=None):
        return ('COUNT(%s)' if not distinct else 'COUNT(DISTINCT %s)') \
            % self.expand(first)

    def EXTRACT(self, first, what):
        return "EXTRACT(%s FROM %s)" % (what, self.expand(first))

    def EPOCH(self, first):
        return self.EXTRACT(first, 'epoch')

    def LENGTH(self, first):
        return "LENGTH(%s)" % self.expand(first)

    def AGGREGATE(self, first, what):
        return "%s(%s)" % (what, self.expand(first))

    def JOIN(self):
        return 'JOIN'

    def LEFT_JOIN(self):
        return 'LEFT JOIN'

    def RANDOM(self):
        return 'Random()'

    def NOT_NULL(self, default, field_type):
        return 'NOT NULL DEFAULT %s' % self.represent(default, field_type)

    def COALESCE(self, first, second):
        expressions = [self.expand(first)]+[self.expand(e) for e in second]
        return 'COALESCE(%s)' % ','.join(expressions)

    def COALESCE_ZERO(self, first):
        return 'COALESCE(%s,0)' % self.expand(first)

    def RAW(self, first):
        return first

    def ALLOW_NULL(self):
        return ''

    def SUBSTRING(self, field, parameters):
        return 'SUBSTR(%s,%s,%s)' % (self.expand(field), parameters[0], parameters[1])

    def PRIMARY_KEY(self, key):
        return 'PRIMARY KEY(%s)' % key

    def _drop(self, table, mode):
        return ['DROP TABLE %s;' % table.sqlsafe]

    def drop(self, table, mode=''):
        db = table._db
        queries = self._drop(table, mode)
        for query in queries:
            if table._dbt:
                self.log(query + '\n', table)
            self.execute(query)
        db.commit()
        del db[table._tablename]
        del db.tables[db.tables.index(table._tablename)]
        db._remove_references_to(table)
        if table._dbt:
            self.file_delete(table._dbt)
            self.log('success!\n', table)

    def _insert(self, table, fields):
        table_rname = table.sqlsafe
        if fields:
            keys = ','.join(f.sqlsafe_name for f, v in fields)
            values = ','.join(self.expand(v, f.type) for f, v in fields)
            return 'INSERT INTO %s(%s) VALUES (%s);' % (table_rname, keys, values)
        else:
            return self._insert_empty(table)

    def _insert_empty(self, table):
        return 'INSERT INTO %s DEFAULT VALUES;' % (table.sqlsafe)

    def insert(self, table, fields):
        query = self._insert(table, fields)
        try:
            self.execute(query)
        except Exception:
            e = sys.exc_info()[1]
            if hasattr(table, '_on_insert_error'):
                return table._on_insert_error(table, fields, e)
            raise e
        if hasattr(table, '_primarykey'):
            mydict = dict([(k[0].name, k[1]) for k in fields if k[0].name in table._primarykey])
            if mydict != {}:
                return mydict
        id = self.lastrowid(table)
        if hasattr(table, '_primarykey') and len(table._primarykey) == 1:
            id = {table._primarykey[0]: id}
        if not isinstance(id, (int, long)):
            return id
        rid = Reference(id)
        (rid._table, rid._record) = (table, None)
        return rid

    def bulk_insert(self, table, items):
        return [self.insert(table, item) for item in items]

    def NOT(self, first):
        return '(NOT %s)' % self.expand(first)

    def AND(self, first, second):
        return '(%s AND %s)' % (self.expand(first), self.expand(second))

    def OR(self, first, second):
        return '(%s OR %s)' % (self.expand(first), self.expand(second))

    def BELONGS(self, first, second):
        if isinstance(second, str):
            return '(%s IN (%s))' % (self.expand(first), second[:-1])
        if not second:
            return '(1=0)'
        items = ','.join(self.expand(item, first.type) for item in second)
        return '(%s IN (%s))' % (self.expand(first), items)

    def REGEXP(self, first, second):
        """Regular expression operator"""
        raise NotImplementedError

    def LIKE(self, first, second):
        """Case sensitive like operator"""
        raise NotImplementedError

    def ILIKE(self, first, second):
        """Case insensitive like operator"""
        return '(%s LIKE %s)' % (self.expand(first),
                                 self.expand(second, 'string'))

    def STARTSWITH(self, first, second):
        return '(%s LIKE %s)' % (self.expand(first),
                                 self.expand(second+'%', 'string'))

    def ENDSWITH(self, first, second):
        return '(%s LIKE %s)' % (self.expand(first),
                                 self.expand('%'+second, 'string'))

    def CONTAINS(self, first, second, case_sensitive=False):
        if first.type in ('string', 'text', 'json'):
            if isinstance(second, Expression):
                second = Expression(None, self.CONCAT('%', Expression(
                            None, self.REPLACE(second, ('%', '%%'))), '%'))
            else:
                second = '%'+str(second).replace('%', '%%')+'%'
        elif first.type.startswith('list:'):
            if isinstance(second, Expression):
                second = Expression(None, self.CONCAT(
                        '%|', Expression(None, self.REPLACE(
                                Expression(None, self.REPLACE(
                                        second, ('%', '%%'))), ('|', '||'))), '|%'))
            else:
                second = '%|'+str(second).replace('%', '%%')\
                    .replace('|', '||')+'|%'
        op = case_sensitive and self.LIKE or self.ILIKE
        return op(first, second)

    def EQ(self, first, second=None):
        if second is None:
            return '(%s IS NULL)' % self.expand(first)
        return '(%s = %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def NE(self, first, second=None):
        if second is None:
            return '(%s IS NOT NULL)' % self.expand(first)
        return '(%s <> %s)' % (self.expand(first),
                               self.expand(second, first.type))

    def LT(self, first, second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s < None" % first)
        return '(%s < %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def LE(self, first, second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s <= None" % first)
        return '(%s <= %s)' % (self.expand(first),
                               self.expand(second, first.type))

    def GT(self, first, second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s > None" % first)
        return '(%s > %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def GE(self, first, second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s >= None" % first)
        return '(%s >= %s)' % (self.expand(first),
                               self.expand(second, first.type))

    def is_numerical_type(self, ftype):
        return ftype in ('integer', 'boolean', 'double', 'bigint') or \
            ftype.startswith('decimal')

    def REPLACE(self, first, (second, third)):
        return 'REPLACE(%s,%s,%s)' % (self.expand(first, 'string'),
                                      self.expand(second, 'string'),
                                      self.expand(third, 'string'))

    def CONCAT(self, *items):
        return '(%s)' % ' || '.join(self.expand(x, 'string') for x in items)

    def ADD(self, first, second):
        if self.is_numerical_type(first.type) or isinstance(first.type, Field):
            return '(%s + %s)' % (self.expand(first),
                                  self.expand(second, first.type))
        else:
            return self.CONCAT(first, second)

    def SUB(self, first, second):
        return '(%s - %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def MUL(self, first, second):
        return '(%s * %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def DIV(self, first, second):
        return '(%s / %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def MOD(self, first, second):
        return '(%s %% %s)' % (self.expand(first),
                               self.expand(second, first.type))

    def AS(self, first, second):
        return '%s AS %s' % (self.expand(first), second)

    def ON(self, first, second):
        table_rname = self.table_alias(first)
        if use_common_filters(second):
            second = self.common_filter(second, [first._tablename])
        return ('%s ON %s') % (self.expand(table_rname), self.expand(second))

    def INVERT(self, first):
        return '%s DESC' % self.expand(first)

    def COMMA(self, first, second):
        return '%s, %s' % (self.expand(first), self.expand(second))

    def CAST(self, first, second):
        return 'CAST(%s AS %s)' % (first, second)

    def expand(self, expression, field_type=None, colnames=False):
        if isinstance(expression, Field):
            et = expression.table
            if not colnames:
                table_rname = et._ot and self.QUOTE_TEMPLATE % et._tablename or et._rname or self.QUOTE_TEMPLATE % et._tablename
                out = '%s.%s' % (table_rname, expression._rname or (self.QUOTE_TEMPLATE % (expression.name)))
            else:
                out = '%s.%s' % (self.QUOTE_TEMPLATE % et._tablename, self.QUOTE_TEMPLATE % expression.name)
            if field_type == 'string' \
                    and not expression.type in ('string', 'text', 'json',
                                                'password'):
                out = self.CAST(out, self.types['text'])
            return out
        elif isinstance(expression, (Expression, Query)):
            first = expression.first
            second = expression.second
            op = expression.op
            optional_args = expression.optional_args or {}
            if not second is None:
                out = op(first, second, **optional_args)
            elif not first is None:
                out = op(first, **optional_args)
            elif isinstance(op, str):
                if op.endswith(';'):
                    op = op[:-1]
                out = '(%s)' % op
            else:
                out = op()
            return out
        elif field_type:
            return str(self.represent(expression, field_type))
        elif isinstance(expression, (list, tuple)):
            return ','.join(self.represent(item, field_type) \
                                for item in expression)
        elif isinstance(expression, bool):
            return '1' if expression else '0'
        else:
            return str(expression)

    def table_alias(self, tbl):
        if not isinstance(tbl, Table):
            tbl = self.db[tbl]
        return tbl.sqlsafe_alias

    def alias(self, table, alias):
        """
        Given a table object, makes a new table object
        with alias name.
        """
        other = copy.copy(table)
        other['_ot'] = other._ot or other.sqlsafe
        other['ALL'] = SQLALL(other)
        other['_tablename'] = alias
        for fieldname in other.fields:
            other[fieldname] = copy.copy(other[fieldname])
            other[fieldname]._tablename = alias
            other[fieldname].tablename = alias
            other[fieldname].table = other
        table._db[alias] = other
        return other

    def _truncate(self, table, mode=''):
        return ['TRUNCATE TABLE %s %s;' % (table.sqlsafe, mode or '')]

    def truncate(self, table, mode= ' '):
        # Prepare functions "write_to_logfile" and "close_logfile"
        try:
            queries = table._db._adapter._truncate(table, mode)
            for query in queries:
                self.log(query + '\n', table)
                self.execute(query)
            self.log('success!\n', table)
        finally:
            pass

    def _update(self, tablename, query, fields):
        if query:
            if use_common_filters(query):
                query = self.common_filter(query, [tablename])
            sql_w = ' WHERE ' + self.expand(query)
        else:
            sql_w = ''
        sql_v = ','.join(['%s=%s' % (field.sqlsafe_name,
                                     self.expand(value, field.type)) \
                              for (field, value) in fields])
        tablename = self.db[tablename].sqlsafe
        return 'UPDATE %s SET %s%s;' % (tablename, sql_v, sql_w)

    def update(self, tablename, query, fields):
        sql = self._update(tablename, query, fields)
        try:
            self.execute(sql)
        except Exception:
            e = sys.exc_info()[1]
            table = self.db[tablename]
            if hasattr(table, '_on_update_error'):
                return table._on_update_error(table, query, fields, e)
            raise e
        try:
            return self.cursor.rowcount
        except:
            return None

    def _delete(self, tablename, query):
        if query:
            if use_common_filters(query):
                query = self.common_filter(query, [tablename])
            sql_w = ' WHERE ' + self.expand(query)
        else:
            sql_w = ''
        tablename = self.db[tablename].sqlsafe
        return 'DELETE FROM %s%s;' % (tablename, sql_w)

    def delete(self, tablename, query):
        sql = self._delete(tablename, query)
        ### special code to handle CASCADE in SQLite & SpatiaLite
        db = self.db
        table = db[tablename]
        if self.dbengine in ('sqlite', 'spatialite') and table._referenced_by:
            deleted = [x[table._id.name] for x in db(query).select(table._id)]
        ### end special code to handle CASCADE in SQLite & SpatiaLite
        self.execute(sql)
        try:
            counter = self.cursor.rowcount
        except:
            counter = None
        ### special code to handle CASCADE in SQLite & SpatiaLite
        if self.dbengine in ('sqlite', 'spatialite') and counter:
            for field in table._referenced_by:
                if field.type == 'reference '+table._tablename \
                        and field.ondelete == 'CASCADE':
                    db(field.belongs(deleted)).delete()
        ### end special code to handle CASCADE in SQLite & SpatiaLite
        return counter

    def get_table(self, query):
        tablenames = self.tables(query)
        if len(tablenames) == 1:
            return tablenames[0]
        elif len(tablenames) < 1:
            raise RuntimeError("No table selected")
        else:
            raise RuntimeError("Too many tables selected")

    def expand_all(self, fields, tablenames):
        db = self.db
        new_fields = []
        append = new_fields.append
        for item in fields:
            if isinstance(item, SQLALL):
                new_fields += item._table
            elif isinstance(item, str):
                m = self.REGEX_TABLE_DOT_FIELD.match(item)
                if m:
                    tablename, fieldname = m.groups()
                    append(db[tablename][fieldname])
                else:
                    append(Expression(db, lambda item=item: item))
            else:
                append(item)
        # ## if no fields specified take them all from the requested tables
        if not new_fields:
            for table in tablenames:
                for field in db[table]:
                    append(field)
        return new_fields

    def _select(self, query, fields, attributes):
        tables = self.tables
        for key in set(attributes.keys())-SELECT_ARGS:
            raise SyntaxError('invalid select attribute: %s' % key)
        args_get = attributes.get
        tablenames = tables(query)
        tablenames_for_common_filters = tablenames
        for field in fields:
            if isinstance(field, basestring):
                m = self.REGEX_TABLE_DOT_FIELD.match(field)
                if m:
                    tn, fn = m.groups()
                    field = self.db[tn][fn]
            for tablename in tables(field):
                if not tablename in tablenames:
                    tablenames.append(tablename)

        if len(tablenames) < 1:
            raise SyntaxError('Set: no tables selected')

        def colexpand(field):
            return self.expand(field, colnames=True)

        self._colnames = map(colexpand, fields)

        def geoexpand(field):
            if isinstance(field.type, str) and field.type.startswith('geo') and isinstance(field, Field):
                field = field.st_astext()
            return self.expand(field)

        sql_f = ', '.join(map(geoexpand, fields))
        sql_o = ''
        sql_s = ''
        left = args_get('left', False)
        inner_join = args_get('join', False)
        distinct = args_get('distinct', False)
        groupby = args_get('groupby', False)
        orderby = args_get('orderby', False)
        having = args_get('having', False)
        limitby = args_get('limitby', False)
        orderby_on_limitby = args_get('orderby_on_limitby', True)
        for_update = args_get('for_update', False)
        if self.can_select_for_update is False and for_update is True:
            raise SyntaxError('invalid select attribute: for_update')
        if distinct is True:
            sql_s += 'DISTINCT'
        elif distinct:
            sql_s += 'DISTINCT ON (%s)' % distinct
        if inner_join:
            icommand = self.JOIN()
            if not isinstance(inner_join, (tuple, list)):
                inner_join = [inner_join]
            ijoint = [t._tablename for t in inner_join
                      if not isinstance(t, Expression)]
            ijoinon = [t for t in inner_join if isinstance(t, Expression)]
            itables_to_merge={} #issue 490
            [itables_to_merge.update(
                    dict.fromkeys(tables(t))) for t in ijoinon]
            ijoinont = [t.first._tablename for t in ijoinon]
            [itables_to_merge.pop(t) for t in ijoinont
             if t in itables_to_merge] #issue 490
            iimportant_tablenames = ijoint + ijoinont + itables_to_merge.keys()
            iexcluded = [t for t in tablenames
                         if not t in iimportant_tablenames]
        if left:
            join = attributes['left']
            command = self.LEFT_JOIN()
            if not isinstance(join, (tuple, list)):
                join = [join]
            joint = [t._tablename for t in join
                     if not isinstance(t, Expression)]
            joinon = [t for t in join if isinstance(t, Expression)]
            #patch join+left patch (solves problem with ordering in left joins)
            tables_to_merge={}
            [tables_to_merge.update(
                    dict.fromkeys(tables(t))) for t in joinon]
            joinont = [t.first._tablename for t in joinon]
            [tables_to_merge.pop(t) for t in joinont if t in tables_to_merge]
            tablenames_for_common_filters = [t for t in tablenames
                        if not t in joinont ]
            important_tablenames = joint + joinont + tables_to_merge.keys()
            excluded = [t for t in tablenames
                        if not t in important_tablenames ]
        else:
            excluded = tablenames

        if use_common_filters(query):
            query = self.common_filter(query, tablenames_for_common_filters)
        sql_w = ' WHERE ' + self.expand(query) if query else ''

        if inner_join and not left:
            sql_t = ', '.join([self.table_alias(t)
                               for t in iexcluded + itables_to_merge.keys()])
            for t in ijoinon:
                sql_t += ' %s %s' % (icommand, t)
        elif not inner_join and left:
            sql_t = ', '.join([self.table_alias(t)
                               for t in excluded + tables_to_merge.keys()])
            if joint:
                sql_t += ' %s %s' % (command,
                                     ','.join([t for t in joint]))
            for t in joinon:
                sql_t += ' %s %s' % (command, t)
        elif inner_join and left:
            all_tables_in_query = set(important_tablenames +
                                      iimportant_tablenames + tablenames)
            tables_in_joinon = set(joinont + ijoinont)
            tables_not_in_joinon = \
                all_tables_in_query.difference(tables_in_joinon)
            sql_t = ','.join([self.table_alias(t) for t in tables_not_in_joinon])
            for t in ijoinon:
                sql_t += ' %s %s' % (icommand, t)
            if joint:
                sql_t += ' %s %s' % (command,
                                     ','.join([t for t in joint]))
            for t in joinon:
                sql_t += ' %s %s' % (command, t)
        else:
            sql_t = ', '.join(self.table_alias(t) for t in tablenames)
        if groupby:
            if isinstance(groupby, (list, tuple)):
                groupby = xorify(groupby)
            sql_o += ' GROUP BY %s' % self.expand(groupby)
            if having:
                sql_o += ' HAVING %s' % attributes['having']
        if orderby:
            if isinstance(orderby, (list, tuple)):
                orderby = xorify(orderby)
            if str(orderby) == '<random>':
                sql_o += ' ORDER BY %s' % self.RANDOM()
            else:
                sql_o += ' ORDER BY %s' % self.expand(orderby)
        if (limitby and not groupby and tablenames and orderby_on_limitby and not orderby):
            sql_o += ' ORDER BY %s' % ', '.join(
                [self.db[t].sqlsafe + '.' + self.db[t][x].sqlsafe_name for t in tablenames for x in (
                    hasattr(self.db[t], '_primarykey') and self.db[t]._primarykey
                    or ['_id']
                    )
                 ]
                )
        # oracle does not support limitby
        sql = self.select_limitby(sql_s, sql_f, sql_t, sql_w, sql_o, limitby)
        if for_update and self.can_select_for_update is True:
            sql = sql.rstrip(';') + ' FOR UPDATE;'
        return sql

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_o += ' LIMIT %i OFFSET %i' % (lmax - lmin, lmin)
        return 'SELECT %s %s FROM %s%s%s;' % \
            (sql_s, sql_f, sql_t, sql_w, sql_o)

    def _fetchall(self):
        return self.cursor.fetchall()

    def _select_aux(self, sql, fields, attributes):
        args_get = attributes.get
        cache = args_get('cache',None)
        if not cache:
            self.execute(sql)
            rows = self._fetchall()
        else:
            (cache_model, time_expire) = cache
            key = self.uri + '/' + sql + '/rows'
            if len(key)>200: key = hashlib_md5(key).hexdigest()
            def _select_aux2():
                self.execute(sql)
                return self._fetchall()
            rows = cache_model(key, _select_aux2, time_expire)
        if isinstance(rows, tuple):
            rows = list(rows)
        limitby = args_get('limitby', None) or (0, )
        rows = self.rowslice(rows, limitby[0], None)
        processor = args_get('processor', self.parse)
        cacheable = args_get('cacheable', False)
        return processor(rows, fields, self._colnames, cacheable=cacheable)

    def select(self, query, fields, attributes):
        """
        Always returns a Rows object, possibly empty.
        """
        sql = self._select(query, fields, attributes)
        cache = attributes.get('cache', None)
        if cache and attributes.get('cacheable', False):
            del attributes['cache']
            (cache_model, time_expire) = cache
            key = self.uri + '/' + sql
            if len(key) > 200: key = hashlib_md5(key).hexdigest()
            args = (sql, fields, attributes)
            return cache_model(
                key,
                lambda self=self, args=args: self._select_aux(*args),
                time_expire)
        else:
            return self._select_aux(sql, fields, attributes)

    def _count(self, query, distinct=None):
        tablenames = self.tables(query)
        if query:
            if use_common_filters(query):
                query = self.common_filter(query, tablenames)
            sql_w = ' WHERE ' + self.expand(query)
        else:
            sql_w = ''
        sql_t = ','.join(self.table_alias(t) for t in tablenames)
        if distinct:
            if isinstance(distinct, (list, tuple)):
                distinct = xorify(distinct)
            sql_d = self.expand(distinct)
            return 'SELECT count(DISTINCT %s) FROM %s%s;' % \
                (sql_d, sql_t, sql_w)
        return 'SELECT count(*) FROM %s%s;' % (sql_t, sql_w)

    def count(self, query, distinct=None):
        self.execute(self._count(query, distinct))
        return self.cursor.fetchone()[0]

    def tables(self, *queries):
        tables = set()
        for query in queries:
            if isinstance(query, Field):
                tables.add(query.tablename)
            elif isinstance(query, (Expression, Query)):
                if not query.first is None:
                    tables = tables.union(self.tables(query.first))
                if not query.second is None:
                    tables = tables.union(self.tables(query.second))
        return list(tables)

    def commit(self):
        if self.connection:
            return self.connection.commit()

    def rollback(self):
        if self.connection:
            return self.connection.rollback()

    def close_connection(self):
        if self.connection:
            r = self.connection.close()
            self.connection = None
            return r

    def distributed_transaction_begin(self, key):
        return

    def prepare(self, key):
        if self.connection: self.connection.prepare()

    def commit_prepared(self, key):
        if self.connection: self.connection.commit()

    def rollback_prepared(self, key):
        if self.connection: self.connection.rollback()

    def concat_add(self, tablename):
        return ', ADD '

    def constraint_name(self, table, fieldname):
        return '%s_%s__constraint' % (table, fieldname)

    def create_sequence_and_triggers(self, query, table, **args):
        self.execute(query)

    def log_execute(self, *a, **b):
        if not self.connection: raise ValueError(a[0])
        if not self.connection: return None
        command = a[0]
        if hasattr(self, 'filter_sql_command'):
            command = self.filter_sql_command(command)
        if self.db._debug:
            LOGGER.debug('SQL: %s' % command)
        self.db._lastsql = command
        t0 = time.time()
        ret = self.cursor.execute(command, *a[1:], **b)
        self.db._timings.append((command, time.time()-t0))
        del self.db._timings[:-TIMINGSSIZE]
        return ret

    def execute(self, *a, **b):
        return self.log_execute(*a, **b)

    def represent(self, obj, fieldtype):
        field_is_type = fieldtype.startswith
        if isinstance(obj, CALLABLETYPES):
            obj = obj()
        if isinstance(fieldtype, SQLCustomType):
            value = fieldtype.encoder(obj)
            if fieldtype.type in ('string', 'text', 'json'):
                return self.adapt(value)
            return value
        if isinstance(obj, (Expression, Field)):
            return str(obj)
        if field_is_type('list:'):
            if not obj:
                obj = []
            elif not isinstance(obj, (list, tuple)):
                obj = [obj]
            if field_is_type('list:string'):
                obj = map(str, obj)
            else:
                obj = map(int, [o for o in obj if o != ''])
        # we don't want to bar_encode json objects
        if isinstance(obj, (list, tuple)) and (not fieldtype == "json"):
            obj = bar_encode(obj)
        if obj is None:
            return 'NULL'
        if obj == '' and not fieldtype[:2] in ['st', 'te', 'js', 'pa', 'up']:
            return 'NULL'
        r = self.represent_exceptions(obj, fieldtype)
        if not r is None:
            return r
        if fieldtype == 'boolean':
            if obj and not str(obj)[:1].upper() in '0F':
                return self.smart_adapt(self.TRUE)
            else:
                return self.smart_adapt(self.FALSE)
        if fieldtype == 'id' or fieldtype == 'integer':
            return str(long(obj))
        if field_is_type('decimal'):
            return str(obj)
        elif field_is_type('reference'): # reference
            # check for tablename first
            referenced = fieldtype[9:].strip()
            if referenced in self.db.tables:
                return str(long(obj))
            p = referenced.partition('.')
            if p[2] != '':
                try:
                    ftype = self.db[p[0]][p[2]].type
                    return self.represent(obj, ftype)
                except (ValueError, KeyError):
                    return repr(obj)
            elif isinstance(obj, (Row, Reference)):
                return str(obj['id'])
            return str(long(obj))
        elif fieldtype == 'double':
            return repr(float(obj))
        if isinstance(obj, unicode):
            obj = obj.encode(self.db_codec)
        if fieldtype == 'blob':
            obj = base64.b64encode(str(obj))
        elif fieldtype == 'date':
            if isinstance(obj, (datetime.date, datetime.datetime)):
                obj = obj.isoformat()[:10]
            else:
                obj = str(obj)
        elif fieldtype == 'datetime':
            if isinstance(obj, datetime.datetime):
                obj = obj.isoformat(self.T_SEP)[:19]
            elif isinstance(obj, datetime.date):
                obj = obj.isoformat()[:10]+self.T_SEP+'00:00:00'
            else:
                obj = str(obj)
        elif fieldtype == 'time':
            if isinstance(obj, datetime.time):
                obj = obj.isoformat()[:10]
            else:
                obj = str(obj)
        elif fieldtype == 'json':
            if not self.native_json:
                if have_serializers:
                    obj = serializers.json(obj)
                elif simplejson:
                    obj = simplejson.dumps(obj)
                else:
                    raise RuntimeError("missing simplejson")
        if not isinstance(obj, bytes):
            obj = bytes(obj)
        try:
            obj.decode(self.db_codec)
        except:
            obj = obj.decode('latin1').encode(self.db_codec)
        return self.adapt(obj)

    def represent_exceptions(self, obj, fieldtype):
        return None

    def lastrowid(self, table):
        return None

    def rowslice(self, rows, minimum=0, maximum=None):
        """
        By default this function does nothing;
        overload when db does not do slicing.
        """
        return rows

    def parse_value(self, value, field_type, blob_decode=True):
        if field_type != 'blob' and isinstance(value, str):
            try:
                value = value.decode(self.db._db_codec)
            except Exception:
                pass
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        if isinstance(field_type, SQLCustomType):
            value = field_type.decoder(value)
        if not isinstance(field_type, str) or value is None:
            return value
        elif field_type in ('string', 'text', 'password', 'upload', 'dict'):
            return value
        elif field_type.startswith('geo'):
            return value
        elif field_type == 'blob' and not blob_decode:
            return value
        else:
            key = REGEX_TYPE.match(field_type).group(0)
            return self.parsemap[key](value, field_type)

    def parse_reference(self, value, field_type):
        referee = field_type[10:].strip()
        if not '.' in referee:
            value = Reference(value)
            value._table, value._record = self.db[referee], None
        return value

    def parse_boolean(self, value, field_type):
        return value == self.TRUE or str(value)[:1].lower() == 't'

    def parse_date(self, value, field_type):
        if isinstance(value, datetime.datetime):
            return value.date()
        if not isinstance(value, (datetime.date, datetime.datetime)):
            (y, m, d) = map(int, str(value)[:10].strip().split('-'))
            value = datetime.date(y, m, d)
        return value

    def parse_time(self, value, field_type):
        if not isinstance(value, datetime.time):
            time_items = map(int, str(value)[:8].strip().split(':')[:3])
            if len(time_items) == 3:
                (h, mi, s) = time_items
            else:
                (h, mi, s) = time_items + [0]
            value = datetime.time(h, mi, s)
        return value

    def parse_datetime(self, value, field_type):
        if not isinstance(value, datetime.datetime):
            value = str(value)
            date_part, time_part, timezone = value[:10], value[11:19], value[19:]
            if '+' in timezone:
                ms, tz = timezone.split('+')
                h, m = tz.split(':')
                dt = datetime.timedelta(seconds=3600*int(h)+60*int(m))
            elif '-' in timezone:
                ms, tz = timezone.split('-')
                h, m = tz.split(':')
                dt = -datetime.timedelta(seconds=3600*int(h)+60*int(m))
            else:
                dt = None
            (y, m, d) = map(int, date_part.split('-'))
            time_parts = time_part and time_part.split(':')[:3] or (0, 0, 0)
            while len(time_parts)<3: time_parts.append(0)
            time_items = map(int, time_parts)
            (h, mi, s) = time_items
            value = datetime.datetime(y, m, d, h, mi, s)
            if dt:
                value = value + dt
        return value

    def parse_blob(self, value, field_type):
        return base64.b64decode(str(value))

    def parse_decimal(self, value, field_type):
        decimals = int(field_type[8:-1].split(',')[-1])
        if self.dbengine in ('sqlite', 'spatialite'):
            value = ('%.' + str(decimals) + 'f') % value
        if not isinstance(value, decimal.Decimal):
            value = decimal.Decimal(str(value))
        return value

    def parse_list_integers(self, value, field_type):
        if not isinstance(self, NoSQLAdapter):
            value = bar_decode_integer(value)
        return value

    def parse_list_references(self, value, field_type):
        if not isinstance(self, NoSQLAdapter):
            value = bar_decode_integer(value)
        return [self.parse_reference(r, field_type[5:]) for r in value]

    def parse_list_strings(self, value, field_type):
        if not isinstance(self, NoSQLAdapter):
            value = bar_decode_string(value)
        return value

    def parse_id(self, value, field_type):
        return long(value)

    def parse_integer(self, value, field_type):
        return long(value)

    def parse_double(self, value, field_type):
        return float(value)

    def parse_json(self, value, field_type):
        if not self.native_json:
            if not isinstance(value, basestring):
                raise RuntimeError('json data not a string')
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            if have_serializers:
                value = serializers.loads_json(value)
            elif simplejson:
                value = simplejson.loads(value)
            else:
                raise RuntimeError("missing simplejson")
        return value

    def build_parsemap(self):
        self.parsemap = {'id': self.parse_id,
                         'integer': self.parse_integer,
                         'bigint': self.parse_integer,
                         'float': self.parse_double,
                         'double': self.parse_double,
                         'reference': self.parse_reference,
                         'boolean': self.parse_boolean,
                         'date': self.parse_date,
                         'time': self.parse_time,
                         'datetime': self.parse_datetime,
                         'blob': self.parse_blob,
                         'decimal': self.parse_decimal,
                         'json': self.parse_json,
                         'list:integer': self.parse_list_integers,
                         'list:reference': self.parse_list_references,
                         'list:string': self.parse_list_strings,
                         }

    def parse(self, rows, fields, colnames, blob_decode=True,
              cacheable=False):
        db = self.db
        virtualtables = []
        new_rows = []
        tmps = []
        for colname in colnames:
            col_m = self.REGEX_TABLE_DOT_FIELD.match(colname)
            if not col_m:
                tmps.append(None)
            else:
                tablename, fieldname = col_m.groups()
                table = db[tablename]
                field = table[fieldname]
                ft = field.type
                tmps.append((tablename, fieldname, table, field, ft))
        for (i, row) in enumerate(rows):
            new_row = Row()
            for (j, colname) in enumerate(colnames):
                value = row[j]
                tmp = tmps[j]
                if tmp:
                    (tablename, fieldname, table, field, ft) = tmp
                    colset = new_row.get(tablename, None)
                    if colset is None:
                        colset = new_row[tablename] = Row()
                        if tablename not in virtualtables:
                            virtualtables.append(tablename)
                    value = self.parse_value(value, ft, blob_decode)
                    if field.filter_out:
                        value = field.filter_out(value)
                    colset[fieldname] = value

                    # for backward compatibility
                    if ft == 'id' and fieldname != 'id' \
                            and not 'id' in table.fields:
                        colset['id'] = value

                    if ft == 'id' and not cacheable:
                        # temporary hack to deal with
                        # GoogleDatastoreAdapter
                        # references
                        if isinstance(self, GoogleDatastoreAdapter):
                            id = value.key.id() if self.use_ndb else value.key().id_or_name()
                            colset[fieldname] = id
                            colset.gae_item = value
                        else:
                            id = value
                        colset.update_record = RecordUpdater(colset, table, id)
                        colset.delete_record = RecordDeleter(table, id)
                        if table._db._lazy_tables:
                            colset['__get_lazy_reference__'] = LazyReferenceGetter(table, id)
                        for rfield in table._referenced_by:
                            referee_link = db._referee_name and \
                                db._referee_name % dict(
                                table=rfield.tablename, field=rfield.name)
                            if referee_link and not referee_link in colset:
                                colset[referee_link] = LazySet(rfield, id)
                else:
                    if not '_extra' in new_row:
                        new_row['_extra'] = Row()
                    new_row['_extra'][colname] = \
                        self.parse_value(value,
                                         fields[j].type, blob_decode)
                    new_column_name = \
                        REGEX_SELECT_AS_PARSER.search(colname)
                    if not new_column_name is None:
                        column_name = new_column_name.groups(0)
                        setattr(new_row, column_name[0], value)
            new_rows.append(new_row)
        rowsobj = Rows(db, new_rows, colnames, rawrows=rows)

        for tablename in virtualtables:
            table = db[tablename]
            fields_virtual = [(f, v) for (f, v) in table.iteritems()
                              if isinstance(v, FieldVirtual)]
            fields_lazy = [(f, v) for (f, v) in table.iteritems()
                           if isinstance(v, FieldMethod)]
            if fields_virtual or fields_lazy:
                for row in rowsobj.records:
                    box = row[tablename]
                    for f, v in fields_virtual:
                        try:
                            box[f] = v.f(row)
                        except AttributeError:
                            pass  # not enough fields to define virtual field
                    for f, v in fields_lazy:
                        try:
                            box[f] = (v.handler or VirtualCommand)(v.f, row)
                        except AttributeError:
                            pass  # not enough fields to define virtual field

            ### old style virtual fields
            for item in table.virtualfields:
                try:
                    rowsobj = rowsobj.setvirtualfields(**{tablename:item})
                except (KeyError, AttributeError):
                    # to avoid breaking virtualfields when partial select
                    pass
        return rowsobj

    def common_filter(self, query, tablenames):
        tenant_fieldname = self.db._request_tenant

        for tablename in tablenames:
            table = self.db[tablename]

            # deal with user provided filters
            if table._common_filter != None:
                query = query & table._common_filter(query)

            # deal with multi_tenant filters
            if tenant_fieldname in table:
                default = table[tenant_fieldname].default
                if not default is None:
                    newquery = table[tenant_fieldname] == default
                    if query is None:
                        query = newquery
                    else:
                        query = query & newquery
        return query

    def CASE(self, query, t, f):
        def represent(x):
            types = {type(True):'boolean', type(0):'integer', type(1.0):'double'}
            if x is None: return 'NULL'
            elif isinstance(x, Expression): return str(x)
            else: return self.represent(x, types.get(type(x), 'string'))
        return Expression(self.db, 'CASE WHEN %s THEN %s ELSE %s END' % \
                              (self.expand(query), represent(t), represent(f)))

    def sqlsafe_table(self, tablename, ot=None):
        if ot is not None:
            return ('%s AS ' + self.QUOTE_TEMPLATE) % (ot, tablename)
        return self.QUOTE_TEMPLATE % tablename

    def sqlsafe_field(self, fieldname):
        return self.QUOTE_TEMPLATE % fieldname


###################################################################################
# List of all the available adapters; they all extend BaseAdapter.
###################################################################################
class SQLiteAdapter(BaseAdapter):
    drivers = ('sqlite2', 'sqlite3')

    can_select_for_update = None    # support ourselves with BEGIN TRANSACTION

    def EXTRACT(self, field, what):
        return "web2py_extract('%s',%s)" % (what, self.expand(field))

    @staticmethod
    def web2py_extract(lookup, s):
        table = {'year': (0, 4),
                 'month': (5, 7),
                 'day': (8, 10),
                 'hour': (11, 13),
                 'minute': (14, 16),
                 'second': (17, 19),
                 }
        try:
            if lookup != 'epoch':
                (i, j) = table[lookup]
                return int(s[i:j])
            else:
                return time.mktime(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S').timetuple())
        except:
            return None

    @staticmethod
    def web2py_regexp(expression, item):
        return re.compile(expression).search(item) is not None

    def __init__(self, db, uri, pool_size=0, folder=None, db_codec='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "sqlite"
        self.uri = uri
        self.adapter_args = adapter_args
        if do_connect: self.find_driver(adapter_args)
        self.pool_size = 0
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        path_encoding = sys.getfilesystemencoding() \
            or locale.getdefaultlocale()[1] or 'utf8'
        if uri.startswith('sqlite:memory'):
            self.dbpath = ':memory:'
        else:
            self.dbpath = uri.split('://', 1)[1]
            if self.dbpath[0] != '/':
                if PYTHON_VERSION[0] == 2:
                    self.dbpath = pjoin(
                        self.folder.decode(path_encoding).encode('utf8'), self.dbpath)
                else:
                    self.dbpath = pjoin(self.folder, self.dbpath)
        if not 'check_same_thread' in driver_args:
            driver_args['check_same_thread'] = False
        if not 'detect_types' in driver_args and do_connect:
            driver_args['detect_types'] = self.driver.PARSE_DECLTYPES

        def connector(dbpath=self.dbpath, driver_args=driver_args):
            return self.driver.Connection(dbpath, **driver_args)

        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.connection.create_function('web2py_extract', 2,
                                        SQLiteAdapter.web2py_extract)
        self.connection.create_function("REGEXP", 2,
                                        SQLiteAdapter.web2py_regexp)

        if self.adapter_args.get('foreign_keys', True):
            self.execute('PRAGMA foreign_keys=ON;')

    def _truncate(self, table, mode=''):
        tablename = table._tablename
        return ['DELETE FROM %s;' % tablename,
                "DELETE FROM sqlite_sequence WHERE name='%s';" % tablename]

    def lastrowid(self, table):
        return self.cursor.lastrowid

    def REGEXP(self, first, second):
        return '(%s REGEXP %s)' % (self.expand(first),
                                   self.expand(second, 'string'))

    def select(self, query, fields, attributes):
        """
        Simulate `SELECT ... FOR UPDATE` with `BEGIN IMMEDIATE TRANSACTION`.
        Note that the entire database, rather than one record, is locked
        (it will be locked eventually anyway by the following UPDATE).
        """
        if attributes.get('for_update', False) and not 'cache' in attributes:
            self.execute('BEGIN IMMEDIATE TRANSACTION;')
        return super(SQLiteAdapter, self).select(query, fields, attributes)


class MySQLAdapter(BaseAdapter):
    drivers = ('MySQLdb', 'pymysql', 'mysqlconnector')

    commit_on_alter_table = True
    support_distributed_transaction = True
    types = {'boolean': 'CHAR(1)',
             'string': 'VARCHAR(%(length)s)',
             'text': 'LONGTEXT',
             'json': 'LONGTEXT',
             'password': 'VARCHAR(%(length)s)',
             'blob': 'LONGBLOB',
             'upload': 'VARCHAR(%(length)s)',
             'integer': 'INT',
             'bigint': 'BIGINT',
             'float': 'FLOAT',
             'double': 'DOUBLE',
             'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
             'date': 'DATE',
             'time': 'TIME',
             'datetime': 'DATETIME',
             'id': 'INT AUTO_INCREMENT NOT NULL',
             'reference': 'INT, INDEX %(index_name)s (%(field_name)s), FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
             'list:integer': 'LONGTEXT',
             'list:string': 'LONGTEXT',
             'list:reference': 'LONGTEXT',
             'big-id': 'BIGINT AUTO_INCREMENT NOT NULL',
             'big-reference': 'BIGINT, INDEX %(index_name)s (%(field_name)s), FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
             'reference FK': ', CONSTRAINT  `FK_%(constraint_name)s` FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
             }

    QUOTE_TEMPLATE = "`%s`"

    def varquote(self, name):
        return varquote_aux(name, '`%s`')

    def RANDOM(self):
        return 'RAND()'

    def SUBSTRING(self, field, parameters):
        return 'SUBSTRING(%s,%s,%s)' % (self.expand(field),
                                        parameters[0], parameters[1])

    def EPOCH(self, first):
        return "UNIX_TIMESTAMP(%s)" % self.expand(first)

    def CONCAT(self, *items):
        return 'CONCAT(%s)' % ','.join(self.expand(x, 'string') for x in items)

    def REGEXP(self, first, second):
        return '(%s REGEXP %s)' % (self.expand(first),
                                   self.expand(second, 'string'))

    def _drop(self, table, mode):
        # breaks db integrity but without this mysql does not drop table
        table_rname = table.sqlsafe
        return ['SET FOREIGN_KEY_CHECKS=0;','DROP TABLE %s;' % table_rname,
                'SET FOREIGN_KEY_CHECKS=1;']

    def _insert_empty(self, table):
        return 'INSERT INTO %s VALUES (DEFAULT);' % (table.sqlsafe)

    def distributed_transaction_begin(self, key):
        self.execute('XA START;')

    def prepare(self, key):
        self.execute("XA END;")
        self.execute("XA PREPARE;")

    def commit_prepared(self,key):
        self.execute("XA COMMIT;")

    def rollback_prepared(self,key):
        self.execute("XA ROLLBACK;")

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>[^?]+)(\?set_encoding=(?P<charset>\w+))?$')

    def __init__(self, db, uri, pool_size=0, folder=None, db_codec='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "mysql"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args, uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://', 1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError(
                "Invalid URI string in DAL: %s" % self.uri)
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        port = int(m.group('port') or '3306')
        charset = m.group('charset') or 'utf8'
        driver_args.update(db=db,
                           user=credential_decoder(user),
                           passwd=credential_decoder(password),
                           host=host,
                           port=port,
                           charset=charset)

        def connector(driver_args=driver_args):
            return self.driver.connect(**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.execute('SET FOREIGN_KEY_CHECKS=1;')
        self.execute("SET sql_mode='NO_BACKSLASH_ESCAPES';")

    def lastrowid(self, table):
        self.execute('select last_insert_id();')
        return int(self.cursor.fetchone()[0])


def uuid2int(uuidv):
    return uuid.UUID(uuidv).int

def int2uuid(n):
    return str(uuid.UUID(int=n))

def cleanup(text):
    """
    Validates that the given text is clean: only contains [0-9a-zA-Z_]
    """
    # if not REGEX_ALPHANUMERIC.match(text):
    #     raise SyntaxError('invalid table or field name: %s' % text)
    return text


########################################################################
# end of adapters
########################################################################

ADAPTERS = {'sqlite': SQLiteAdapter,
            'mysql': MySQLAdapter
            }


def sqlhtml_validators(field):
    """
    Field type validation, using web2py's validators mechanism.

    makes sure the content of a field is in line with the declared
    fieldtype
    """
    db = field.db
    try:
        from gluon import validators
    except ImportError:
        return []
    field_type, field_length = field.type, field.length
    if isinstance(field_type, SQLCustomType):
        if hasattr(field_type, 'validator'):
            return field_type.validator
        else:
            field_type = field_type.type
    elif not isinstance(field_type, str):
        return []
    requires = []

    def ff(r, id):
        row = r(id)
        if not row:
            return id
        elif hasattr(r, '_format') and isinstance(r._format, str):
            return r._format % row
        elif hasattr(r, '_format') and callable(r._format):
            return r._format(row)
        else:
            return id
    if field_type in (('string', 'text', 'password')):
        requires.append(validators.IS_LENGTH(field_length))
    elif field_type == 'json':
        requires.append(validators.IS_EMPTY_OR(validators.IS_JSON(native_json=field.db._adapter.native_json)))
    elif field_type == 'double' or field_type == 'float':
        requires.append(validators.IS_FLOAT_IN_RANGE(-1e100, 1e100))
    elif field_type == 'integer':
        requires.append(validators.IS_INT_IN_RANGE(-2**31, 2**31))
    elif field_type == 'bigint':
        requires.append(validators.IS_INT_IN_RANGE(-2**63, 2**63))
    elif field_type.startswith('decimal'):
        requires.append(validators.IS_DECIMAL_IN_RANGE(-10**10, 10**10))
    elif field_type == 'date':
        requires.append(validators.IS_DATE())
    elif field_type == 'time':
        requires.append(validators.IS_TIME())
    elif field_type == 'datetime':
        requires.append(validators.IS_DATETIME())
    elif db and field_type.startswith('reference') and \
            field_type.find('.') < 0 and \
            field_type[10:] in db.tables:
        referenced = db[field_type[10:]]

        def repr_ref(id, row=None, r=referenced, f=ff): return f(r, id)

        field.represent = field.represent or repr_ref
        if hasattr(referenced, '_format') and referenced._format:
            requires = validators.IS_IN_DB(db, referenced._id,
                                           referenced._format)
            if field.unique:
                requires._and = validators.IS_NOT_IN_DB(db, field)
            if field.tablename == field_type[10:]:
                return validators.IS_EMPTY_OR(requires)
            return requires
    elif db and field_type.startswith('list:reference') and \
            field_type.find('.') < 0 and \
            field_type[15:] in db.tables:
        referenced = db[field_type[15:]]

        def list_ref_repr(ids, row=None, r=referenced, f=ff):
            if not ids:
                return None
            refs = None
            db, id = r._db, r._id
            if isinstance(db._adapter, GoogleDatastoreAdapter):
                def count(values): return db(id.belongs(values)).select(id)
                rx = range(0, len(ids), 30)
                refs = reduce(lambda a, b:a&b, [count(ids[i:i+30]) for i in rx])
            else:
                refs = db(id.belongs(ids)).select(id)
            return (refs and ', '.join(f(r, x.id) for x in refs) or '')

        field.represent = field.represent or list_ref_repr
        if hasattr(referenced, '_format') and referenced._format:
            requires = validators.IS_IN_DB(db, referenced._id,
                                           referenced._format, multiple=True)
        else:
            requires = validators.IS_IN_DB(db, referenced._id,
                                           multiple=True)
        if field.unique:
            requires._and = validators.IS_NOT_IN_DB(db, field)
        if not field.notnull:
            requires = validators.IS_EMPTY_OR(requires)
        return requires
    elif field_type.startswith('list:'):
        def repr_list(values, row=None): return', '.join(str(v) for v in (values or []))
        field.represent = field.represent or repr_list
    if field.unique:
        requires.insert(0, validators.IS_NOT_IN_DB(db, field))
    sff = ['in', 'do', 'da', 'ti', 'de', 'bo']
    if field.notnull and not field_type[:2] in sff:
        requires.insert(0, validators.IS_NOT_EMPTY())
    elif not field.notnull and field_type[:2] in sff and requires:
        requires[-1] = validators.IS_EMPTY_OR(requires[-1])
    return requires


def bar_escape(item):
    return str(item).replace('|', '||')


def bar_encode(items):
    return '|%s|' % '|'.join(bar_escape(item) for item in items if str(item).strip())


def bar_decode_integer(value):
    if not hasattr(value, 'split') and hasattr(value, 'read'):
        value = value.read()
    return [long(x) for x in value.split('|') if x.strip()]


def bar_decode_string(value):
    return [x.replace('||', '|') for x in
            REGEX_UNPACK.split(value[1:-1]) if x.strip()]


class Row(object):

    """
    A dictionary that lets you do d['a'] as well as d.a
    this is only used to store a `Row`
    """

    __init__ = lambda self, *args, **kwargs: self.__dict__.update(*args, **kwargs)

    def __getitem__(self, k):
        if isinstance(k, Table):
            try:
                return ogetattr(self, k._tablename)
            except (KeyError, AttributeError, TypeError):
                pass
        elif isinstance(k, Field):
            try:
                return ogetattr(self, k.name)
            except (KeyError, AttributeError, TypeError):
                pass
            try:
                return ogetattr(ogetattr(self, k.tablename), k.name)
            except (KeyError, AttributeError, TypeError):
                pass

        key = str(k)
        _extra = ogetattr(self, '__dict__').get('_extra', None)
        if _extra is not None:
            v = _extra.get(key, DEFAULT)
            if v != DEFAULT:
                return v
        try:
            return ogetattr(self, key)
        except (KeyError, AttributeError, TypeError):
            pass

        m = REGEX_TABLE_DOT_FIELD.match(key)
        if m:
            try:
                return ogetattr(self, m.group(1))[m.group(2)]
            except (KeyError, AttributeError, TypeError):
                key = m.group(2)
        try:
            return ogetattr(self, key)
        except (KeyError, AttributeError, TypeError), ae:
            try:
                self[key] = ogetattr(self, '__get_lazy_reference__')(key)
                return self[key]
            except:
                raise ae

    __setitem__ = lambda self, key, value: setattr(self, str(key), value)

    __delitem__ = object.__delattr__

    __copy__ = lambda self: Row(self)

    __call__ = __getitem__

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except(KeyError, AttributeError, TypeError):
            return self.__dict__.get(key, default)

    has_key = __contains__ = lambda self, key: key in self.__dict__

    __nonzero__ = lambda self: len(self.__dict__)>0

    update = lambda self, *args, **kwargs:  self.__dict__.update(*args, **kwargs)

    keys = lambda self: self.__dict__.keys()

    items = lambda self: self.__dict__.items()

    values = lambda self: self.__dict__.values()

    __iter__ = lambda self: self.__dict__.__iter__()

    iteritems = lambda self: self.__dict__.iteritems()

    __str__ = __repr__ = lambda self: '<Row %s>' % self.as_dict()

    __int__ = lambda self: object.__getattribute__(self, 'id')

    __long__ = lambda self: long(object.__getattribute__(self, 'id'))

    __getattr__ = __getitem__

    # def __getattribute__(self, key):
    #     try:
    #         return object.__getattribute__(self, key)
    #     except AttributeError, ae:
    #         try:
    #             return self.__get_lazy_reference__(key)
    #         except:
    #             raise ae

    def __eq__(self, other):
        try:
            return self.as_dict() == other.as_dict()
        except AttributeError:
            return False

    def __ne__(self, other):
        return not (self == other)

    def __copy__(self):
        return Row(dict(self))

    def as_dict(self, datetime_to_str=False, custom_types=None):
        SERIALIZABLE_TYPES = [str, unicode, int, long, float, bool, list, dict]
        if isinstance(custom_types, (list, tuple, set)):
            SERIALIZABLE_TYPES += custom_types
        elif custom_types:
            SERIALIZABLE_TYPES.append(custom_types)
        d = dict(self)
        for k in copy.copy(d.keys()):
            v=d[k]
            if d[k] is None:
                continue
            elif isinstance(v, Row):
                d[k]=v.as_dict()
            elif isinstance(v, Reference):
                d[k]=long(v)
            elif isinstance(v, decimal.Decimal):
                d[k]=float(v)
            elif isinstance(v, (datetime.date, datetime.datetime, datetime.time)):
                if datetime_to_str:
                    d[k] = v.isoformat().replace('T', ' ')[:19]
            elif not isinstance(v, tuple(SERIALIZABLE_TYPES)):
                del d[k]
        return d

    def as_xml(self, row_name="row", colnames=None, indent='  '):

        def f(row, field, indent='  '):
            if isinstance(row, Row):
                spc = indent+'  \n'
                items = [f(row[x], x, indent+'  ') for x in row]
                return '%s<%s>\n%s\n%s</%s>' % (
                    indent,
                    field,
                    spc.join(item for item in items if item),
                    indent,
                    field)
            elif not callable(row):
                if REGEX_ALPHANUMERIC.match(field):
                    return '%s<%s>%s</%s>' % (indent, field, row, field)
                else:
                    return '%s<extra name="%s">%s</extra>' % \
                        (indent, field, row)
            else:
                return None
        return f(self, row_name, indent=indent)

    def as_json(self, mode="object", default=None, colnames=None,
                serialize=True, **kwargs):
        """
        serializes the row to a JSON object
        kwargs are passed to .as_dict method
        only "object" mode supported

        `serialize = False` used by Rows.as_json

        TODO: return array mode with query column order

        mode and colnames are not implemented
        """

        item = self.as_dict(**kwargs)
        if serialize:
            if have_serializers:
                return serializers.json(item,
                                        default=default or
                                        serializers.custom_json)
            elif simplejson:
                return simplejson.dumps(item)
            else:
                raise RuntimeError("missing simplejson")
        else:
            return item


################################################################################
# Everything below should be independent of the specifics of the database
# and should work for RDBMs and some NoSQL databases
################################################################################

class SQLCallableList(list):
    def __call__(self):
        return copy.copy(self)


def smart_query(fields, text):
    if not isinstance(fields, (list, tuple)):
        fields = [fields]
    new_fields = []
    for field in fields:
        if isinstance(field, Field):
            new_fields.append(field)
        elif isinstance(field, Table):
            for ofield in field:
                new_fields.append(ofield)
        else:
            raise RuntimeError("fields must be a list of fields")
    fields = new_fields
    field_map = {}
    for field in fields:
        n = field.name.lower()
        if not n in field_map:
            field_map[n] = field
        n = str(field).lower()
        if not n in field_map:
            field_map[n] = field
    constants = {}
    i = 0
    while True:
        m = REGEX_CONST_STRING.search(text)
        if not m: break
        text = text[:m.start()]+('#%i' % i)+text[m.end():]
        constants[str(i)] = m.group()[1:-1]
        i+=1
    text = re.sub('\s+', ' ', text).lower()
    for a, b in [('&', 'and'),
                 ('|', 'or'),
                 ('~', 'not'),
                 ('==', '='),
                 ('<', '<'),
                 ('>', '>'),
                 ('<=', '<='),
                 ('>=', '>='),
                 ('<>', '!='),
                 ('=<', '<='),
                 ('=>', '>='),
                 ('=', '='),
                 (' less or equal than ', '<='),
                 (' greater or equal than ', '>='),
                 (' equal or less than ', '<='),
                 (' equal or greater than ', '>='),
                 (' less or equal ', '<='),
                 (' greater or equal ', '>='),
                 (' equal or less ', '<='),
                 (' equal or greater ', '>='),
                 (' not equal to ', '!='),
                 (' not equal ', '!='),
                 (' equal to ', '='),
                 (' equal ', '='),
                 (' equals ', '='),
                 (' less than ', '<'),
                 (' greater than ', '>'),
                 (' starts with ', 'startswith'),
                 (' ends with ', 'endswith'),
                 (' not in ', 'notbelongs'),
                 (' in ', 'belongs'),
                 (' is ', '=')]:
        if a[0]==' ':
            text = text.replace(' is'+a, ' %s ' % b)
        text = text.replace(a, ' %s ' % b)
    text = re.sub('\s+', ' ', text).lower()
    text = re.sub('(?P<a>[\<\>\!\=])\s+(?P<b>[\<\>\!\=])', '\g<a>\g<b>', text)
    query = field = neg = op = logic = None
    for item in text.split():
        if field is None:
            if item == 'not':
                neg = True
            elif not neg and not logic and item in ('and', 'or'):
                logic = item
            elif item in field_map:
                field = field_map[item]
            else:
                raise RuntimeError("Invalid syntax")
        elif not field is None and op is None:
            op = item
        elif not op is None:
            if item.startswith('#'):
                if not item[1:] in constants:
                    raise RuntimeError("Invalid syntax")
                value = constants[item[1:]]
            else:
                value = item
                if field.type in ('text', 'string', 'json'):
                    if op == '=': op = 'like'
            if op == '=': new_query = field == value
            elif op == '<': new_query = field < value
            elif op == '>': new_query = field > value
            elif op == '<=': new_query = field <= value
            elif op == '>=': new_query = field >= value
            elif op == '!=': new_query = field != value
            elif op == 'belongs': new_query = field.belongs(value.split(','))
            elif op == 'notbelongs': new_query = ~field.belongs(value.split(','))
            elif field.type in ('text', 'string', 'json'):
                if op == 'contains': new_query = field.contains(value)
                elif op == 'like': new_query = field.like(value)
                elif op == 'startswith': new_query = field.startswith(value)
                elif op == 'endswith': new_query = field.endswith(value)
                else: raise RuntimeError("Invalid operation")
            elif field._db._adapter.dbengine == 'google:datastore' and \
                 field.type in ('list:integer', 'list:string', 'list:reference'):
                if op == 'contains': new_query = field.contains(value)
                else: raise RuntimeError("Invalid operation")
            else: raise RuntimeError("Invalid operation")
            if neg: new_query = ~new_query
            if query is None:
                query = new_query
            elif logic == 'and':
                query &= new_query
            elif logic == 'or':
                query |= new_query
            field = op = neg = logic = None
    return query


class DAL(object):

    """
    An instance of this class represents a database connection

    Args:
        uri(str): contains information for connecting to a database.
            Defaults to `'sqlite://dummy.db'`

            Note:
                experimental: you can specify a dictionary as uri
                parameter i.e. with::

                    db = DAL({"uri": "sqlite://storage.sqlite",
                              "tables": {...}, ...})

                for an example of dict input you can check the output
                of the scaffolding db model with

                    db.as_dict()

                Note that for compatibility with Python older than
                version 2.6.5 you should cast your dict input keys
                to str due to a syntax limitation on kwarg names.
                for proper DAL dictionary input you can use one of::

                    obj = serializers.cast_keys(dict, [encoding="utf-8"])
                    #or else (for parsing json input)
                    obj = serializers.loads_json(data, unicode_keys=False)

        pool_size: How many open connections to make to the database object.
        folder: where .table files will be created. Automatically set within
            web2py. Use an explicit path when using DAL outside web2py
        db_codec: string encoding of the database (default: 'UTF-8')
        table_hash: database identifier with .tables. If your connection hash
                    change you can still using old .tables if they have db_hash
                    as prefix
        check_reserved: list of adapters to check tablenames and column names
            against sql/nosql reserved keywords. Defaults to `None`

            - 'common' List of sql keywords that are common to all database
              types such as "SELECT, INSERT". (recommended)
            - 'all' Checks against all known SQL keywords
            - '<adaptername>'' Checks against the specific adapters list of
              keywords
            - '<adaptername>_nonreserved' Checks against the specific adapters
              list of nonreserved keywords. (if available)

        migrate: sets default migrate behavior for all tables
        fake_migrate: sets default fake_migrate behavior for all tables
        migrate_enabled: If set to False disables ALL migrations
        fake_migrate_all: If set to True fake migrates ALL tables
        attempts: Number of times to attempt connecting
        auto_import: If set to True, tries import automatically table
            definitions from the databases folder (works only for simple models)
        bigint_id: If set, turn on bigint instead of int for id and reference
            fields
        lazy_tables: delaya table definition until table access
        after_connection: can a callable that will be executed after the
            connection

    Example:
        Use as::

           db = DAL('sqlite://test.db')

        or::

           db = DAL(**{"uri": ..., "tables": [...]...}) # experimental

           db.define_table('tablename', Field('fieldname1'),
                                        Field('fieldname2'))


    """

    def __new__(cls, uri='sqlite://dummy.db', *args, **kwargs):
        if not hasattr(THREAD_LOCAL, 'db_instances'):
            THREAD_LOCAL.db_instances = {}
        if not hasattr(THREAD_LOCAL, 'db_instances_zombie'):
            THREAD_LOCAL.db_instances_zombie = {}
        if uri == '<zombie>':
            db_uid = kwargs['db_uid']  # a zombie must have a db_uid!
            if db_uid in THREAD_LOCAL.db_instances:
                db_group = THREAD_LOCAL.db_instances[db_uid]
                db = db_group[-1]
            elif db_uid in THREAD_LOCAL.db_instances_zombie:
                db = THREAD_LOCAL.db_instances_zombie[db_uid]
            else:
                db = super(DAL, cls).__new__(cls)
                THREAD_LOCAL.db_instances_zombie[db_uid] = db
        else:
            db_uid = kwargs.get('db_uid', hashlib_md5(repr(uri)).hexdigest())
            if db_uid in THREAD_LOCAL.db_instances_zombie:
                db = THREAD_LOCAL.db_instances_zombie[db_uid]
                del THREAD_LOCAL.db_instances_zombie[db_uid]
            else:
                db = super(DAL, cls).__new__(cls)
            db_group = THREAD_LOCAL.db_instances.get(db_uid, [])
            db_group.append(db)
            THREAD_LOCAL.db_instances[db_uid] = db_group
        db._db_uid = db_uid
        return db

    @staticmethod
    def set_folder(folder):
        # ## this allows gluon to set a folder for this thread
        # ## <<<<<<<<< Should go away as new DAL replaces old sql.py
        BaseAdapter.set_folder(folder)

    @staticmethod
    def get_instances():
        """
        Returns a dictionary with uri as key with timings and defined tables::

            {'sqlite://storage.sqlite': {
                'dbstats': [(select auth_user.email from auth_user, 0.02009)],
                'dbtables': {
                    'defined': ['auth_cas', 'auth_event', 'auth_group',
                        'auth_membership', 'auth_permission', 'auth_user'],
                    'lazy': '[]'
                    }
                }
            }

        """
        dbs = getattr(THREAD_LOCAL, 'db_instances', {}).items()
        infos = {}
        for db_uid, db_group in dbs:
            for db in db_group:
                if not db._uri:
                    continue
                k = hide_password(db._adapter.uri)
                infos[k] = dict(dbstats=[(row[0], row[1]) for row in db._timings],
                                dbtables={'defined': sorted(list(set(db.tables)-set(db._LAZY_TABLES.keys()))),
                                          'lazy': sorted(db._LAZY_TABLES.keys())})
        return infos

    @staticmethod
    def distributed_transaction_begin(*instances):
        if not instances:
            return
        thread_key = '%s.%s' % (socket.gethostname(), threading.currentThread())
        keys = ['%s.%i' % (thread_key, i) for (i, db) in instances]
        instances = enumerate(instances)
        for (i, db) in instances:
            if not db._adapter.support_distributed_transaction():
                raise SyntaxError(
                    'distributed transaction not suported by %s' % db._dbname)
        for (i, db) in instances:
            db._adapter.distributed_transaction_begin(keys[i])

    @staticmethod
    def distributed_transaction_commit(*instances):
        if not instances:
            return
        instances = enumerate(instances)
        thread_key = '%s.%s' % (socket.gethostname(), threading.currentThread())
        keys = ['%s.%i' % (thread_key, i) for (i, db) in instances]
        for (i, db) in instances:
            if not db._adapter.support_distributed_transaction():
                raise SyntaxError(
                    'distributed transaction not suported by %s' % db._dbanme)
        try:
            for (i, db) in instances:
                db._adapter.prepare(keys[i])
        except:
            for (i, db) in instances:
                db._adapter.rollback_prepared(keys[i])
            raise RuntimeError('failure to commit distributed transaction')
        else:
            for (i, db) in instances:
                db._adapter.commit_prepared(keys[i])
        return

    def __init__(self, uri=DEFAULT_URI,
                 pool_size=0, folder=None,
                 db_codec='UTF-8', check_reserved=None,
                 migrate=True, fake_migrate=False,
                 migrate_enabled=True, fake_migrate_all=False,
                 decode_credentials=False, driver_args=None,
                 adapter_args=None, attempts=5, auto_import=False,
                 bigint_id=False, debug=False, lazy_tables=False,
                 db_uid=None, do_connect=True,
                 after_connection=None, tables=None, ignore_field_case=True,
                 entity_quoting=False, table_hash=None):

        if uri == '<zombie>' and db_uid is not None: return
        if not decode_credentials:
            credential_decoder = lambda cred: cred
        else:
            credential_decoder = lambda cred: urllib.unquote(cred)
        self._folder = folder
        if folder:
            self.set_folder(folder)
        self._uri = uri
        self._pool_size = pool_size
        self._db_codec = db_codec
        self._lastsql = ''
        self._timings = []
        self._pending_references = {}
        self._request_tenant = 'request_tenant'
        self._common_fields = []
        self._referee_name = '%(table)s'
        self._bigint_id = bigint_id
        self._debug = debug
        self._migrated = []
        self._LAZY_TABLES = {}
        self._lazy_tables = lazy_tables
        self._tables = SQLCallableList()
        self._driver_args = driver_args
        self._adapter_args = adapter_args
        self._check_reserved = check_reserved
        self._decode_credentials = decode_credentials
        self._attempts = attempts
        self._do_connect = do_connect
        self._ignore_field_case = ignore_field_case

        if not str(attempts).isdigit() or attempts < 0:
            attempts = 5
        if uri:
            uris = isinstance(uri, (list, tuple)) and uri or [uri]
            error = ''
            connected = False
            for k in range(attempts):
                for uri in uris:
                    try:
                        if is_jdbc and not uri.startswith('jdbc:'):
                            uri = 'jdbc:'+uri
                        self._dbname = REGEX_DBNAME.match(uri).group()
                        if not self._dbname in ADAPTERS:
                            raise SyntaxError("Error in URI '%s' or database not supported" % self._dbname)
                        # notice that driver args or {} else driver_args
                        # defaults to {} global, not correct
                        kwargs = dict(db=self,
                                      uri=uri,
                                      pool_size=pool_size,
                                      folder=folder,
                                      db_codec=db_codec,
                                      credential_decoder=credential_decoder,
                                      driver_args=driver_args or {},
                                      adapter_args=adapter_args or {},
                                      do_connect=do_connect,
                                      after_connection=after_connection,
                                      entity_quoting=entity_quoting)
                        self._adapter = ADAPTERS[self._dbname](**kwargs)
                        types = ADAPTERS[self._dbname].types
                        # copy so multiple DAL() possible
                        self._adapter.types = copy.copy(types)
                        self._adapter.build_parsemap()
                        self._adapter.ignore_field_case = ignore_field_case
                        if bigint_id:
                            if 'big-id' in types and 'reference' in types:
                                self._adapter.types['id'] = types['big-id']
                                self._adapter.types['reference'] = types['big-reference']
                        connected = True
                        break
                    except SyntaxError:
                        raise
                    except Exception:
                        tb = traceback.format_exc()
                        LOGGER.debug('DEBUG: connect attempt %i, connection error:\n%s' % (k, tb))
                if connected:
                    break
                else:
                    time.sleep(1)
            if not connected:
                raise RuntimeError("Failure to connect, tried %d times:\n%s" % (attempts, tb))
        else:
            self._adapter = BaseAdapter(db=self, pool_size=0,
                                        uri='None', folder=folder,
                                        db_codec=db_codec, after_connection=after_connection,
                                        entity_quoting=entity_quoting)
            migrate = fake_migrate = False
        adapter = self._adapter
        self._uri_hash = table_hash or hashlib_md5(adapter.uri).hexdigest()
        self.check_reserved = check_reserved
        if self.check_reserved:
            from reserved_sql_keywords import ADAPTERS as RSK
            self.RSK = RSK
        self._migrate = migrate
        self._fake_migrate = fake_migrate
        self._migrate_enabled = migrate_enabled
        self._fake_migrate_all = fake_migrate_all
        if auto_import or tables:
            self.import_table_definitions(adapter.folder,
                                          tables=tables)

    @property
    def tables(self):
        return self._tables

    def import_table_definitions(self, path, migrate=False,
                                 fake_migrate=False, tables=None):
        if tables:
            for table in tables:
                self.define_table(**table)
        else:
            pattern = pjoin(path, self._uri_hash+'_*.table')
            for filename in glob.glob(pattern):
                tfile = self._adapter.file_open(filename, 'r')
                try:
                    sql_fields = pickle.load(tfile)
                    name = filename[len(pattern)-7:-6]
                    mf = [(value['sortable'],
                           Field(key,
                                 type=value['type'],
                                 length=value.get('length', None),
                                 notnull=value.get('notnull', False),
                                 unique=value.get('unique', False))) \
                              for key, value in sql_fields.iteritems()]
                    mf.sort(lambda a, b: cmp(a[0], b[0]))
                    self.define_table(name, *[item[1] for item in mf],
                                      **dict(migrate=migrate,
                                             fake_migrate=fake_migrate))
                finally:
                    self._adapter.file_close(tfile)

    def check_reserved_keyword(self, name):
        """
        Validates `name` against SQL keywords
        Uses self.check_reserve which is a list of operators to use.
        """
        for backend in self.check_reserved:
            if name.upper() in self.RSK[backend]:
                raise SyntaxError(
                    'invalid table/column name "%s" is a "%s" reserved SQL/NOSQL keyword' % (name, backend.upper()))

    def parse_as_rest(self, patterns, args, vars, queries=None, nested_select=True):
        """
        Example:
            Use as::

                db.define_table('person', Field('name'), Field('info'))
                db.define_table('pet',
                    Field('ownedby', db.person),
                    Field('name'), Field('info')
                )

                @request.restful()
                def index():
                    def GET(*args, **vars):
                        patterns = [
                            "/friends[person]",
                            "/{person.name}/:field",
                            "/{person.name}/pets[pet.ownedby]",
                            "/{person.name}/pets[pet.ownedby]/{pet.name}",
                            "/{person.name}/pets[pet.ownedby]/{pet.name}/:field",
                            ("/dogs[pet]", db.pet.info=='dog'),
                            ("/dogs[pet]/{pet.name.startswith}", db.pet.info=='dog'),
                            ]
                        parser = db.parse_as_rest(patterns, args, vars)
                        if parser.status == 200:
                            return dict(content=parser.response)
                        else:
                            raise HTTP(parser.status, parser.error)

                    def POST(table_name, **vars):
                        if table_name == 'person':
                            return db.person.validate_and_insert(**vars)
                        elif table_name == 'pet':
                            return db.pet.validate_and_insert(**vars)
                        else:
                            raise HTTP(400)
                    return locals()
        """

        db = self
        re1 = REGEX_SEARCH_PATTERN
        re2 = REGEX_SQUARE_BRACKETS

        def auto_table(table, base='', depth=0):
            patterns = []
            for field in db[table].fields:
                if base:
                    tag = '%s/%s' % (base, field.replace('_', '-'))
                else:
                    tag = '/%s/%s' % (table.replace('_', '-'), field.replace('_', '-'))
                f = db[table][field]
                if not f.readable: continue
                if f.type == 'id' or 'slug' in field or f.type.startswith('reference'):
                    tag += '/{%s.%s}' % (table, field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type.startswith('boolean'):
                    tag += '/{%s.%s}' % (table, field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type in ('float', 'double', 'integer', 'bigint'):
                    tag += '/{%s.%s.ge}/{%s.%s.lt}' % (table, field, table, field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type.startswith('list:'):
                    tag += '/{%s.%s.contains}' % (table, field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type in ('date', 'datetime'):
                    tag += '/{%s.%s.year}' % (table, field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag += '/{%s.%s.month}' % (table, field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag += '/{%s.%s.day}' % (table, field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                if f.type in ('datetime', 'time'):
                    tag += '/{%s.%s.hour}' % (table, field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag += '/{%s.%s.minute}' % (table, field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag += '/{%s.%s.second}' % (table, field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                if depth>0:
                    for f in db[table]._referenced_by:
                        tag+='/%s[%s.%s]' % (table, f.tablename, f.name)
                        patterns.append(tag)
                        patterns += auto_table(table, base=tag, depth=depth-1)
            return patterns

        if patterns == 'auto':
            patterns=[]
            for table in db.tables:
                if not table.startswith('auth_'):
                    patterns.append('/%s[%s]' % (table, table))
                    patterns += auto_table(table, base='', depth=1)
        else:
            i = 0
            while i < len(patterns):
                pattern = patterns[i]
                if not isinstance(pattern, str):
                    pattern = pattern[0]
                tokens = pattern.split('/')
                if tokens[-1].startswith(':auto') and re2.match(tokens[-1]):
                    new_patterns = auto_table(tokens[-1][tokens[-1].find('[')+1:-1],
                                              '/'.join(tokens[:-1]))
                    patterns = patterns[:i]+new_patterns+patterns[i+1:]
                    i += len(new_patterns)
                else:
                    i += 1
        if '/'.join(args) == 'patterns':
            return Row({'status': 200, 'pattern': 'list',
                        'error': None, 'response': patterns})
        for pattern in patterns:
            basequery, exposedfields = None, []
            if isinstance(pattern, tuple):
                if len(pattern) == 2:
                    pattern, basequery = pattern
                elif len(pattern) > 2:
                    pattern, basequery, exposedfields = pattern[0:3]
            otable = table = None
            if not isinstance(queries, dict):
                dbset = db(queries)
                if basequery is not None:
                    dbset = dbset(basequery)
            i = 0
            tags = pattern[1:].split('/')
            if len(tags) != len(args):
                continue
            for tag in tags:
                if re1.match(tag):
                    # print 're1:'+tag
                    tokens = tag[1:-1].split('.')
                    table, field = tokens[0], tokens[1]
                    if not otable or table == otable:
                        if len(tokens) == 2 or tokens[2] == 'eq':
                            query = db[table][field] == args[i]
                        elif tokens[2] == 'ne':
                            query = db[table][field] != args[i]
                        elif tokens[2] == 'lt':
                            query = db[table][field] < args[i]
                        elif tokens[2] == 'gt':
                            query = db[table][field] > args[i]
                        elif tokens[2] == 'ge':
                            query = db[table][field] >= args[i]
                        elif tokens[2] == 'le':
                            query = db[table][field] <= args[i]
                        elif tokens[2] == 'year':
                            query = db[table][field].year() == args[i]
                        elif tokens[2] == 'month':
                            query = db[table][field].month() == args[i]
                        elif tokens[2] == 'day':
                            query = db[table][field].day() == args[i]
                        elif tokens[2] == 'hour':
                            query = db[table][field].hour() == args[i]
                        elif tokens[2] == 'minute':
                            query = db[table][field].minutes() == args[i]
                        elif tokens[2] == 'second':
                            query = db[table][field].seconds() == args[i]
                        elif tokens[2] == 'startswith':
                            query = db[table][field].startswith(args[i])
                        elif tokens[2] == 'contains':
                            query = db[table][field].contains(args[i])
                        else:
                            raise RuntimeError("invalid pattern: %s" % pattern)
                        if len(tokens) == 4 and tokens[3] == 'not':
                            query = ~query
                        elif len(tokens) >= 4:
                            raise RuntimeError("invalid pattern: %s" % pattern)
                        if not otable and isinstance(queries, dict):
                            dbset = db(queries[table])
                            if basequery is not None:
                                dbset = dbset(basequery)
                        dbset = dbset(query)
                    else:
                        raise RuntimeError("missing relation in pattern: %s" % pattern)
                elif re2.match(tag) and args[i]==tag[:tag.find('[')]:
                    ref = tag[tag.find('[')+1:-1]
                    if '.' in ref and otable:
                        table, field = ref.split('.')
                        selfld = '_id'
                        if db[table][field].type.startswith('reference '):
                            refs = [x.name for x in db[otable] if x.type == db[table][field].type]
                        else:
                            refs = [x.name for x in db[table]._referenced_by if x.tablename==otable]
                        if refs:
                            selfld = refs[0]
                        if nested_select:
                            try:
                                dbset=db(db[table][field].belongs(dbset._select(db[otable][selfld])))
                            except ValueError:
                                return Row({'status': 400, 'pattern': pattern,
                                            'error': 'invalid path', 'response': None})
                        else:
                            items = [item.id for item in dbset.select(db[otable][selfld])]
                            dbset = db(db[table][field].belongs(items))
                    else:
                        table = ref
                        if not otable and isinstance(queries, dict):
                            dbset = db(queries[table])
                        dbset = dbset(db[table])
                elif tag == ':field' and table:
                    # print 're3:'+tag
                    field = args[i]
                    if not field in db[table]: break
                    # hand-built patterns should respect .readable=False as well
                    if not db[table][field].readable:
                        return Row({'status': 418, 'pattern': pattern,
                                    'error': 'I\'m a teapot', 'response': None})
                    try:
                        distinct = vars.get('distinct', False) == 'True'
                        offset = long(vars.get('offset', None) or 0)
                        limits = (offset, long(vars.get('limit', None) or 1000)+offset)
                    except ValueError:
                        return Row({'status': 400 ,'error': 'invalid limits', 'response': None})
                    items =  dbset.select(db[table][field], distinct=distinct, limitby=limits)
                    if items:
                        return Row({'status': 200, 'response': items,
                                    'pattern': pattern})
                    else:
                        return Row({'status': 404, 'pattern': pattern,
                                    'error': 'no record found', 'response': None})
                elif tag != args[i]:
                    break
                otable = table
                i += 1
                if i == len(tags) and table:
                    if hasattr(db[table], '_id'):
                        ofields = vars.get('order', db[table]._id.name).split('|')
                    else:
                        ofields = vars.get('order', db[table]._primarykey[0]).split('|')
                    try:
                        orderby = [db[table][f] if not f.startswith('~') else ~db[table][f[1:]] for f in ofields]
                    except (KeyError, AttributeError):
                        return Row({'status': 400, 'error': 'invalid orderby', 'response': None})
                    if exposedfields:
                        fields = [field for field in db[table] if str(field).split('.')[-1] in exposedfields and field.readable]
                    else:
                        fields = [field for field in db[table] if field.readable]
                    count = dbset.count()
                    try:
                        offset = long(vars.get('offset', None) or 0)
                        limits = (offset, long(vars.get('limit', None) or 1000)+offset)
                    except ValueError:
                        return Row({'status': 400, 'error': 'invalid limits', 'response': None})
                    #if count > limits[1]-limits[0]:
                    #    return Row({'status': 400, 'error': 'too many records', 'response': None})
                    try:
                        response = dbset.select(limitby=limits, orderby=orderby, *fields)
                    except ValueError:
                        return Row({'status': 400, 'pattern': pattern,
                                    'error': 'invalid path', 'response': None})
                    return Row({'status': 200, 'response': response,
                                'pattern': pattern, 'count': count})
        return Row({'status': 400, 'error': 'no matching pattern', 'response': None})

    def define_table(self,
                     tablename,
                     *fields,
                     **args
                     ):
        if not fields and 'fields' in args:
            fields = args.get('fields', ())
        if not isinstance(tablename, str):
            if isinstance(tablename, unicode):
                try:
                    tablename = str(tablename)
                except UnicodeEncodeError:
                    raise SyntaxError("invalid unicode table name")
            else:
                raise SyntaxError("missing table name")
        elif hasattr(self, tablename) or tablename in self.tables:
            if not args.get('redefine', False):
                raise SyntaxError('table already defined: %s' % tablename)
        elif tablename.startswith('_') or hasattr(self, tablename) or \
                REGEX_PYTHON_KEYWORDS.match(tablename):
            raise SyntaxError('invalid table name: %s' % tablename)
        elif self.check_reserved:
            self.check_reserved_keyword(tablename)
        else:
            invalid_args = set(args)-TABLE_ARGS
            if invalid_args:
                raise SyntaxError('invalid table "%s" attributes: %s' \
                    % (tablename, invalid_args))
        if self._lazy_tables and not tablename in self._LAZY_TABLES:
            self._LAZY_TABLES[tablename] = (tablename, fields, args)
            table = None
        else:
            table = self.lazy_define_table(tablename, *fields, **args)
        if not tablename in self.tables:
            self.tables.append(tablename)
        return table

    def lazy_define_table(self,
                          tablename,
                          *fields,
                          **args
                          ):
        args_get = args.get
        common_fields = self._common_fields
        if common_fields:
            fields = list(fields) + list(common_fields)

        table_class = args_get('table_class', Table)
        table = table_class(self, tablename, *fields, **args)
        table._actual = True
        self[tablename] = table
        # must follow above line to handle self references
        table._create_references()
        for field in table:
            if field.requires == DEFAULT:
                field.requires = sqlhtml_validators(field)

        migrate = self._migrate_enabled and args_get('migrate', self._migrate)
        if migrate and not self._uri in (None, 'None') \
                or self._adapter.dbengine=='google:datastore':
            fake_migrate = self._fake_migrate_all or \
                args_get('fake_migrate', self._fake_migrate)
            polymodel = args_get('polymodel', None)
            try:
                GLOBAL_LOCKER.acquire()
                self._lastsql = self._adapter.create_table(
                    table, migrate=migrate,
                    fake_migrate=fake_migrate,
                    polymodel=polymodel)
            finally:
                GLOBAL_LOCKER.release()
        else:
            table._dbt = None
        on_define = args_get('on_define', None)
        if on_define: on_define(table)
        return table

    def as_dict(self, flat=False, sanitize=True):
        db_uid = uri = None
        if not sanitize:
            uri, db_uid = (self._uri, self._db_uid)
        db_as_dict = dict(tables=[], uri=uri, db_uid=db_uid,
                          **dict([(k, getattr(self, "_" + k, None))
                          for k in 'pool_size','folder','db_codec',
                          'check_reserved','migrate','fake_migrate',
                          'migrate_enabled','fake_migrate_all',
                          'decode_credentials','driver_args',
                          'adapter_args', 'attempts',
                          'bigint_id','debug','lazy_tables',
                          'do_connect']))
        for table in self:
            db_as_dict["tables"].append(table.as_dict(flat=flat,
                                        sanitize=sanitize))
        return db_as_dict

    def as_xml(self, sanitize=True):
        if not have_serializers:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return serializers.xml(d)

    def as_json(self, sanitize=True):
        if not have_serializers:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return serializers.json(d)

    def as_yaml(self, sanitize=True):
        if not have_serializers:
            raise ImportError("No YAML serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return serializers.yaml(d)

    def __contains__(self, tablename):
        try:
            return tablename in self.tables
        except AttributeError:
            # The instance has no .tables attribute yet
            return False

    has_key = __contains__

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def __iter__(self):
        for tablename in self.tables:
            yield self[tablename]

    def __getitem__(self, key):
        return self.__getattr__(str(key))

    def __getattr__(self, key):
        if ogetattr(self, '_lazy_tables') and \
                key in ogetattr(self, '_LAZY_TABLES'):
            tablename, fields, args = self._LAZY_TABLES.pop(key)
            return self.lazy_define_table(tablename, *fields, **args)
        return ogetattr(self, key)

    def __setitem__(self, key, value):
        osetattr(self, str(key), value)

    def __setattr__(self, key, value):
        if key[:1]!='_' and key in self:
            raise SyntaxError(
                'Object %s exists and cannot be redefined' % key)
        osetattr(self, key, value)

    __delitem__ = object.__delattr__

    def __repr__(self):
        if hasattr(self, '_uri'):
            return '<DAL uri="%s">' % hide_password(self._adapter.uri)
        else:
            return '<DAL db_uid="%s">' % self._db_uid

    def smart_query(self, fields, text):
        return Set(self, smart_query(fields, text))

    def __call__(self, query=None, ignore_common_filters=None):
        if isinstance(query, Table):
            query = self._adapter.id_query(query)
        elif isinstance(query, Field):
            query = query!=None
        elif isinstance(query, dict):
            icf = query.get("ignore_common_filters")
            if icf: ignore_common_filters = icf
        return Set(self, query, ignore_common_filters=ignore_common_filters)

    def commit(self):
        self._adapter.commit()

    def rollback(self):
        self._adapter.rollback()

    def close(self):
        self._adapter.close()
        if self._db_uid in THREAD_LOCAL.db_instances:
            db_group = THREAD_LOCAL.db_instances[self._db_uid]
            db_group.remove(self)
            if not db_group:
                del THREAD_LOCAL.db_instances[self._db_uid]

    def executesql(self, query, placeholders=None, as_dict=False,
                   fields=None, colnames=None, as_ordered_dict=False):
        """
        Executes an arbitrary query

        Args:
            query (str): the query to submit to the backend
            placeholders: is optional and will always be None.
                If using raw SQL with placeholders, placeholders may be
                a sequence of values to be substituted in
                or, (if supported by the DB driver), a dictionary with keys
                matching named placeholders in your SQL.
            as_dict: will always be None when using DAL.
                If using raw SQL can be set to True and the results cursor
                returned by the DB driver will be converted to a sequence of
                dictionaries keyed with the db field names. Results returned
                with as_dict=True are the same as those returned when applying
                .to_list() to a DAL query.  If "as_ordered_dict"=True the
                behaviour is the same as when "as_dict"=True with the keys
                (field names) guaranteed to be in the same order as returned
                by the select name executed on the database.
            fields: list of DAL Fields that match the fields returned from the
                DB. The Field objects should be part of one or more Table
                objects defined on the DAL object. The "fields" list can include
                one or more DAL Table objects in addition to or instead of
                including Field objects, or it can be just a single table
                (not in a list). In that case, the Field objects will be
                extracted from the table(s).

                Note:
                    if either `fields` or `colnames` is provided, the results
                    will be converted to a DAL `Rows` object using the
                    `db._adapter.parse()` method
            colnames: list of field names in tablename.fieldname format

        Note:
            It is also possible to specify both "fields" and the associated
            "colnames". In that case, "fields" can also include DAL Expression
            objects in addition to Field objects. For Field objects in "fields",
            the associated "colnames" must still be in tablename.fieldname
            format. For Expression objects in "fields", the associated
            "colnames" can be any arbitrary labels.

        DAL Table objects referred to by "fields" or "colnames" can be dummy
        tables and do not have to represent any real tables in the database.
        Also, note that the "fields" and "colnames" must be in the
        same order as the fields in the results cursor returned from the DB.

        """
        adapter = self._adapter
        if placeholders:
            adapter.execute(query, placeholders)
        else:
            adapter.execute(query)
        if as_dict or as_ordered_dict:
            if not hasattr(adapter.cursor, 'description'):
                raise RuntimeError("database does not support executesql(...,as_dict=True)")
            # Non-DAL legacy db query, converts cursor results to dict.
            # sequence of 7-item sequences. each sequence tells about a column.
            # first item is always the field name according to Python Database API specs
            columns = adapter.cursor.description
            # reduce the column info down to just the field names
            fields = colnames or [f[0] for f in columns]
            if len(fields) != len(set(fields)):
                raise RuntimeError("Result set includes duplicate column names. Specify unique column names using the 'colnames' argument")

            # will hold our finished resultset in a list
            data = adapter._fetchall()
            # convert the list for each row into a dictionary so it's
            # easier to work with. row['field_name'] rather than row[0]
            if as_ordered_dict:
                _dict = OrderedDict
            else:
                _dict = dict
            return [_dict(zip(fields, row)) for row in data]
        try:
            data = adapter._fetchall()
        except:
            return None
        if fields or colnames:
            fields = [] if fields is None else fields
            if not isinstance(fields, list):
                fields = [fields]
            extracted_fields = []
            for field in fields:
                if isinstance(field, Table):
                    extracted_fields.extend([f for f in field])
                else:
                    extracted_fields.append(field)
            if not colnames:
                colnames = ['%s.%s' % (f.tablename, f.name)
                            for f in extracted_fields]
            data = adapter.parse(
                data, fields=extracted_fields, colnames=colnames)
        return data

    def _remove_references_to(self, thistable):
        for table in self:
            table._referenced_by = [field for field in table._referenced_by
                                    if not field.table==thistable]

    def export_to_csv_file(self, ofile, *args, **kwargs):
        step = long(kwargs.get('max_fetch_rows,', 500))
        write_colnames = kwargs['write_colnames'] = \
            kwargs.get("write_colnames", True)
        for table in self.tables:
            ofile.write('TABLE %s\r\n' % table)
            query = self._adapter.id_query(self[table])
            nrows = self(query).count()
            kwargs['write_colnames'] = write_colnames
            for k in range(0, nrows, step):
                self(query).select(limitby=(k, k+step)).export_to_csv_file(
                    ofile, *args, **kwargs)
                kwargs['write_colnames'] = False
            ofile.write('\r\n\r\n')
        ofile.write('END')

    def import_from_csv_file(self, ifile, id_map=None, null='<NULL>',
                             unique='uuid', map_tablenames=None,
                             ignore_missing_tables=False,
                             *args, **kwargs):
        # if id_map is None: id_map={}
        id_offset = {}  # only used if id_map is None
        map_tablenames = map_tablenames or {}
        for line in ifile:
            line = line.strip()
            if not line:
                continue
            elif line == 'END':
                return
            elif not line.startswith('TABLE ') or \
                    not line[6:] in self.tables:
                raise SyntaxError('invalid file format')
            else:
                tablename = line[6:]
                tablename = map_tablenames.get(tablename, tablename)
                if tablename is not None and tablename in self.tables:
                    self[tablename].import_from_csv_file(
                        ifile, id_map, null, unique, id_offset,
                        *args, **kwargs)
                elif tablename is None or ignore_missing_tables:
                    # skip all non-empty lines
                    for line in ifile:
                        if not line.strip():
                            break
                else:
                    raise RuntimeError("Unable to import table that does not exist.\nTry db.import_from_csv_file(..., map_tablenames={'table':'othertable'},ignore_missing_tables=True)")


def DAL_unpickler(db_uid):
    return DAL('<zombie>', db_uid=db_uid)


def DAL_pickler(db):
    return DAL_unpickler, (db._db_uid,)

copyreg.pickle(DAL, DAL_pickler, DAL_unpickler)


class SQLALL(object):
    """
    Helper class providing a comma-separated string having all the field names
    (prefixed by table name and '.')

    normally only called from within gluon.dal
    """

    def __init__(self, table):
        self._table = table

    def __str__(self):
        return ', '.join([str(field) for field in self._table])


# class Reference(int):
class Reference(long):

    def __allocate(self):
        if not self._record:
            self._record = self._table[long(self)]
        if not self._record:
            raise RuntimeError(
                "Using a recursive select but encountered a broken reference: %s %d"%(self._table, long(self)))

    def __getattr__(self, key):
        if key == 'id':
            return long(self)
        if key in self._table:
            self.__allocate()
        if self._record:
            return self._record.get(key, None)  # to deal with case self.update_record()
        else:
            return None

    def get(self, key, default=None):
        return self.__getattr__(key, default)

    def __setattr__(self, key, value):
        if key.startswith('_'):
            long.__setattr__(self, key, value)
            return
        self.__allocate()
        self._record[key] =  value

    def __getitem__(self, key):
        if key == 'id':
            return long(self)
        self.__allocate()
        return self._record.get(key, None)

    def __setitem__(self, key, value):
        self.__allocate()
        self._record[key] = value


def Reference_unpickler(data):
    return marshal.loads(data)


def Reference_pickler(data):
    try:
        marshal_dump = marshal.dumps(long(data))
    except AttributeError:
        marshal_dump = 'i%s' % struct.pack('<i', long(data))
    return (Reference_unpickler, (marshal_dump,))

copyreg.pickle(Reference, Reference_pickler, Reference_unpickler)


class MethodAdder(object):
    def __init__(self, table):
        self.table = table

    def __call__(self):
        return self.register()

    def __getattr__(self, method_name):
        return self.register(method_name)

    def register(self, method_name=None):
        def _decorated(f):
            instance = self.table
            import types
            method = types.MethodType(f, instance, instance.__class__)
            name = method_name or f.func_name
            setattr(instance, name, method)
            return f
        return _decorated


class Table(object):

    """
    Represents a database table

    Example::
        You can create a table as::
            db = DAL(...)
            db.define_table('users', Field('name'))

        And then::

            db.users.insert(name='me') # print db.users._insert(...) to see SQL
            db.users.drop()

    """

    def __init__(self,
                 db,
                 tablename,
                 *fields,
                 **args):
        """
        Initializes the table and performs checking on the provided fields.

        Each table will have automatically an 'id'.

        If a field is of type Table, the fields (excluding 'id') from that table
        will be used instead.

        Raises:
            SyntaxError: when a supplied field is of incorrect type.
        """
        self._actual = False  # set to True by define_table()
        self._tablename = tablename
        if (not isinstance(tablename, str) or tablename[0] == '_'
            or hasattr(DAL, tablename) or '.' in tablename
            or REGEX_PYTHON_KEYWORDS.match(tablename)
            ):
            raise SyntaxError('Field: invalid table name: %s, '
                              'use rname for "funny" names' % tablename)
        self._ot = None
        self._rname = args.get('rname')
        self._sequence_name = (args.get('sequence_name') or
                               db and db._adapter.sequence_name(self._rname
                                                                or tablename))
        self._trigger_name = (args.get('trigger_name') or
                              db and db._adapter.trigger_name(tablename))
        self._common_filter = args.get('common_filter')
        self._format = args.get('format')
        self._singular = args.get(
            'singular', tablename.replace('_', ' ').capitalize())
        self._plural = args.get(
            'plural', pluralize(self._singular.lower()).capitalize())
        # horrible but for backard compatibility of appamdin:
        if 'primarykey' in args and args['primarykey'] is not None:
            self._primarykey = args.get('primarykey')

        self._before_insert = []
        self._before_update = [Set.delete_uploaded_files]
        self._before_delete = [Set.delete_uploaded_files]
        self._after_insert = []
        self._after_update = []
        self._after_delete = []

        self.add_method = MethodAdder(self)

        fieldnames, newfields=set(), []
        _primarykey = getattr(self, '_primarykey', None)
        if _primarykey is not None:
            if not isinstance(_primarykey, list):
                raise SyntaxError(
                    "primarykey must be a list of fields from table '%s'"
                    % tablename)
            if len(_primarykey) == 1:
                self._id = [f for f in fields if isinstance(f, Field)
                                and f.name ==_primarykey[0]][0]
        elif not [f for f in fields if (isinstance(f, Field) and
                  f.type == 'id') or (isinstance(f, dict) and
                  f.get("type", None) == "id")]:
            field = Field('id', 'id')
            newfields.append(field)
            fieldnames.add('id')
            self._id = field
        virtual_fields = []

        def include_new(field):
            newfields.append(field)
            fieldnames.add(field.name)
            if field.type == 'id':
                self._id = field
        for field in fields:
            if isinstance(field, (FieldMethod, FieldVirtual)):
                virtual_fields.append(field)
            elif isinstance(field, Field) and not field.name in fieldnames:
                if field.db is not None:
                    field = copy.copy(field)
                include_new(field)
            elif isinstance(field, dict) and not field['fieldname'] in fieldnames:
                include_new(Field(**field))
            elif isinstance(field, Table):
                table = field
                for field in table:
                    if not field.name in fieldnames and not field.type == 'id':
                        t2 = not table._actual and self._tablename
                        include_new(field.clone(point_self_references_to=t2))
            elif not isinstance(field, (Field, Table)):
                raise SyntaxError(
                    'define_table argument is not a Field or Table: %s' % field)
        fields = newfields
        self._db = db
        tablename = tablename
        self._fields = SQLCallableList()
        self.virtualfields = []
        fields = list(fields)

        if db and db._adapter.uploads_in_blob is True:
            uploadfields = [f.name for f in fields if f.type == 'blob']
            for field in fields:
                fn = field.uploadfield
                if isinstance(field, Field) and field.type == 'upload'\
                        and fn is True and not field.uploadfs:
                    fn = field.uploadfield = '%s_blob' % field.name
                if isinstance(fn, str) and not fn in uploadfields and not field.uploadfs:
                    fields.append(Field(fn, 'blob', default='',
                                        writable=False, readable=False))

        fieldnames_set = set()
        reserved = dir(Table) + ['fields']
        if (db and db.check_reserved):
            check_reserved = db.check_reserved_keyword
        else:
            def check_reserved(field_name):
                if field_name in reserved:
                    raise SyntaxError("field name %s not allowed" % field_name)
        for field in fields:
            field_name = field.name
            check_reserved(field_name)
            if db and db._ignore_field_case:
                fname_item = field_name.lower()
            else:
                fname_item = field_name
            if fname_item in fieldnames_set:
                raise SyntaxError("duplicate field %s in table %s" %
                                 (field_name, tablename))
            else:
                fieldnames_set.add(fname_item)

            self.fields.append(field_name)
            self[field_name] = field
            if field.type == 'id':
                self['id'] = field
            field.tablename = field._tablename = tablename
            field.table = field._table = self
            field.db = field._db = db
        self.ALL = SQLALL(self)

        if _primarykey is not None:
            for k in _primarykey:
                if k not in self.fields:
                    raise SyntaxError(
                        "primarykey must be a list of fields from table '%s " %
                        tablename)
                else:
                    self[k].notnull = True
        for field in virtual_fields:
            self[field.name] = field

    @property
    def fields(self):
        return self._fields

    def update(self, *args, **kwargs):
        raise RuntimeError("Syntax Not Supported")

    def _enable_record_versioning(self,
                                  archive_db=None,
                                  archive_name='%(tablename)s_archive',
                                  is_active='is_active',
                                  current_record='current_record',
                                  current_record_label=None):
        db = self._db
        archive_db = archive_db or db
        archive_name = archive_name % dict(tablename=self._tablename)
        if archive_name in archive_db.tables():
            return  # do not try define the archive if already exists
        fieldnames = self.fields()
        same_db = archive_db is db
        field_type = self if same_db else 'bigint'
        clones = []
        for field in self:
            nfk = same_db or not field.type.startswith('reference')
            clones.append(
                field.clone(unique=False, type=field.type if nfk else 'bigint')
                )
        archive_db.define_table(
            archive_name,
            Field(current_record, field_type, label=current_record_label),
            *clones, **dict(format=self._format))

        self._before_update.append(
            lambda qset, fs, db=archive_db, an=archive_name, cn=current_record:
                                archive_record(qset, fs, db[an], cn))
        if is_active and is_active in fieldnames:
            self._before_delete.append(
                lambda qset: qset.update(is_active=False))
            newquery = lambda query, t=self, name=self._tablename: \
                reduce(AND, [db[tn].is_active == True
                            for tn in db._adapter.tables(query)
                            if tn == name or getattr(db[tn], '_ot', None)==name])
            query = self._common_filter
            if query:
                newquery = query & newquery
            self._common_filter = newquery

    def _validate(self, **vars):
        errors = Row()
        for key, value in vars.iteritems():
            value, error = self[key].validate(value)
            if error:
                errors[key] = error
        return errors

    def _create_references(self):
        db = self._db
        pr = db._pending_references
        self._referenced_by = []
        self._references = []
        for field in self:
            # fieldname = field.name  ## FIXME not used ?
            field_type = field.type
            if isinstance(field_type, str) and field_type[:10] == 'reference ':
                ref = field_type[10:].strip()
                if not ref:
                    SyntaxError('Table: reference to nothing: %s' % ref)
                if '.' in ref:
                    rtablename, throw_it, rfieldname = ref.partition('.')
                else:
                    rtablename, rfieldname = ref, None
                if not rtablename in db:
                    pr[rtablename] = pr.get(rtablename, []) + [field]
                    continue
                rtable = db[rtablename]
                if rfieldname:
                    if not hasattr(rtable, '_primarykey'):
                        raise SyntaxError(
                            'keyed tables can only reference other keyed tables (for now)')
                    if rfieldname not in rtable.fields:
                        raise SyntaxError(
                            "invalid field '%s' for referenced table '%s'"
                            " in table '%s'" % (rfieldname, rtablename, self._tablename)
                            )
                    rfield = rtable[rfieldname]
                else:
                    rfield = rtable._id
                rtable._referenced_by.append(field)
                field.referent = rfield
                self._references.append(field)
            else:
                field.referent = None
        if self._tablename in pr:
            referees = pr.pop(self._tablename)
            for referee in referees:
                self._referenced_by.append(referee)

    def _filter_fields(self, record, id=False):
        return dict([(k, v) for (k, v) in record.iteritems() if k
                     in self.fields and (self[k].type != 'id' or id)])

    def _build_query(self, key):
        """ for keyed table only """
        query = None
        for k, v in key.iteritems():
            if k in self._primarykey:
                if query:
                    query = query & (self[k] == v)
                else:
                    query = (self[k] == v)
            else:
                raise SyntaxError(
                'Field %s is not part of the primary key of %s'
                % (k, self._tablename)
                )
        return query

    def __getitem__(self, key):
        if not key:
            return None
        elif isinstance(key, dict):
            """ for keyed table """
            query = self._build_query(key)
            return self._db(query).select(limitby=(0, 1), orderby_on_limitby=False).first()
        elif str(key).isdigit() or 'google' in DRIVERS and isinstance(key, Key):
            return self._db(self._id == key).select(limitby=(0, 1), orderby_on_limitby=False).first()
        elif key:
            return ogetattr(self, str(key))

    def __call__(self, key=DEFAULT, **kwargs):
        for_update = kwargs.get('_for_update', False)
        if '_for_update' in kwargs:
            del kwargs['_for_update']

        orderby = kwargs.get('_orderby', None)
        if '_orderby' in kwargs:
            del kwargs['_orderby']

        if not key is DEFAULT:
            if isinstance(key, Query):
                record = self._db(key).select(
                    limitby=(0, 1), for_update=for_update, orderby=orderby, orderby_on_limitby=False).first()
            elif not str(key).isdigit():
                record = None
            else:
                record = self._db(self._id == key).select(
                    limitby=(0, 1), for_update=for_update, orderby=orderby, orderby_on_limitby=False).first()
            if record:
                for k, v in kwargs.iteritems():
                    if record[k]!=v: return None
            return record
        elif kwargs:
            query = reduce(lambda a, b:a&b, [self[k]==v for k, v in kwargs.iteritems()])
            return self._db(query).select(limitby=(0, 1), for_update=for_update, orderby=orderby, orderby_on_limitby=False).first()
        else:
            return None

    def __setitem__(self, key, value):
        if isinstance(key, dict) and isinstance(value, dict):
            """ option for keyed table """
            if set(key.keys()) == set(self._primarykey):
                value = self._filter_fields(value)
                kv = {}
                kv.update(value)
                kv.update(key)
                if not self.insert(**kv):
                    query = self._build_query(key)
                    self._db(query).update(**self._filter_fields(value))
            else:
                raise SyntaxError(
                    'key must have all fields from primary key: %s'
                    % (self._primarykey))
        elif str(key).isdigit():
            if key == 0:
                self.insert(**self._filter_fields(value))
            elif self._db(self._id == key)\
                    .update(**self._filter_fields(value)) is None:
                raise SyntaxError('No such record: %s' % key)
        else:
            if isinstance(key, dict):
                raise SyntaxError(
                    'value must be a dictionary: %s' % value)
            osetattr(self, str(key), value)

    __getattr__ = __getitem__

    def __setattr__(self, key, value):
        if key[:1]!='_' and key in self:
            raise SyntaxError('Object exists and cannot be redefined: %s' % key)
        osetattr(self, key, value)

    def __delitem__(self, key):
        if isinstance(key, dict):
            query = self._build_query(key)
            if not self._db(query).delete():
                raise SyntaxError('No such record: %s' % key)
        elif not str(key).isdigit() or \
                not self._db(self._id == key).delete():
            raise SyntaxError('No such record: %s' % key)

    def __contains__(self, key):
        return hasattr(self, key)

    has_key = __contains__

    def items(self):
        return self.__dict__.items()

    def __iter__(self):
        for fieldname in self.fields:
            yield self[fieldname]

    def iteritems(self):
        return self.__dict__.iteritems()

    def __repr__(self):
        return '<Table %s (%s)>' % (self._tablename, ','.join(self.fields()))

    def __str__(self):
        if self._ot is not None:
            ot = self._ot
            if 'Oracle' in str(type(self._db._adapter)):
                return '%s %s' % (ot, self._tablename)
            return '%s AS %s' % (ot, self._tablename)

        return self._tablename

    @property
    def sqlsafe(self):
        rname = self._rname
        if rname: return rname
        return self._db._adapter.sqlsafe_table(self._tablename)

    @property
    def sqlsafe_alias(self):
        rname = self._rname
        ot = self._ot
        if rname and not ot: return rname
        return self._db._adapter.sqlsafe_table(self._tablename, self._ot)

    def _drop(self, mode=''):
        return self._db._adapter._drop(self, mode)

    def drop(self, mode=''):
        return self._db._adapter.drop(self, mode)

    def _listify(self, fields, update=False):
        new_fields = {}  # format: new_fields[name] = (field, value)

        # store all fields passed as input in new_fields
        for name in fields:
            if not name in self.fields:
                if name != 'id':
                    raise SyntaxError(
                        'Field %s does not belong to the table' % name)
            else:
                field = self[name]
                value = fields[name]
                if field.filter_in:
                    value = field.filter_in(value)
                new_fields[name] = (field, value)

        # check all fields that should be in the table but are not passed
        to_compute = []
        for ofield in self:
            name = ofield.name
            if not name in new_fields:
                # if field is supposed to be computed, compute it!
                if ofield.compute:  # save those to compute for later
                    to_compute.append((name, ofield))
                # if field is required, check its default value
                elif not update and not ofield.default is None:
                    value = ofield.default
                    fields[name] = value
                    new_fields[name] = (ofield, value)
                # if this is an update, user the update field instead
                elif update and not ofield.update is None:
                    value = ofield.update
                    fields[name] = value
                    new_fields[name] = (ofield, value)
                # if the field is still not there but it should, error
                elif not update and ofield.required:
                    raise RuntimeError(
                        'Table: missing required field: %s' % name)
        # now deal with fields that are supposed to be computed
        if to_compute:
            row = Row(fields)
            for name, ofield in to_compute:
                # try compute it
                try:
                    row[name] = new_value = ofield.compute(row)
                    new_fields[name] = (ofield, new_value)
                except (KeyError, AttributeError):
                    # error silently unless field is required!
                    if ofield.required:
                        raise SyntaxError('unable to compute field: %s' % name)
        return new_fields.values()

    def _attempt_upload(self, fields):
        for field in self:
            if field.type == 'upload' and field.name in fields:
                value = fields[field.name]
                if value is not None and not isinstance(value, str):
                    if hasattr(value, 'file') and hasattr(value, 'filename'):
                        new_name = field.store(value.file, filename=value.filename)
                    elif hasattr(value, 'read') and hasattr(value, 'name'):
                        new_name = field.store(value, filename=value.name)
                    else:
                        raise RuntimeError("Unable to handle upload")
                    fields[field.name] = new_name

    def _defaults(self, fields):
        """If there are no fields/values specified, return table defaults"""
        if not fields:
            fields = {}
            for field in self:
                if field.type != "id":
                    fields[field.name] = field.default
        return fields

    def _insert(self, **fields):
        fields = self._defaults(fields)
        return self._db._adapter._insert(self, self._listify(fields))

    def insert(self, **fields):
        fields = self._defaults(fields)
        self._attempt_upload(fields)
        if any(f(fields) for f in self._before_insert): return 0
        ret =  self._db._adapter.insert(self, self._listify(fields))
        if ret and self._after_insert:
            fields = Row(fields)
            [f(fields, ret) for f in self._after_insert]
        return ret

    def validate_and_insert(self, **fields):
        response = Row()
        response.errors = Row()
        new_fields = copy.copy(fields)
        for key, value in fields.iteritems():
            value, error = self[key].validate(value)
            if error:
                response.errors[key] = "%s" % error
            else:
                new_fields[key] = value
        if not response.errors:
            response.id = self.insert(**new_fields)
        else:
            response.id = None
        return response

    def validate_and_update(self, _key=DEFAULT, **fields):
        response = Row()
        response.errors = Row()
        new_fields = copy.copy(fields)

        for key, value in fields.iteritems():
            value, error = self[key].validate(value)
            if error:
                response.errors[key] = "%s" % error
            else:
                new_fields[key] = value

        if _key is DEFAULT:
            record = self(**fields)
        elif isinstance(_key, dict):
            record = self(**_key)
        else:
            record = self(_key)

        if not response.errors and record:
            if '_id' in self:
                myset = self._db(self._id == record[self._id.name])
            else:
                query = None
                for key, value in _key.iteritems():
                    if query is None:
                        query = getattr(self, key) == value
                    else:
                        query = query & (getattr(self, key) == value)
                myset = self._db(query)
            response.id = myset.update(**fields)
        else:
            response.id = None
        return response

    def update_or_insert(self, _key=DEFAULT, **values):
        if _key is DEFAULT:
            record = self(**values)
        elif isinstance(_key, dict):
            record = self(**_key)
        else:
            record = self(_key)
        if record:
            record.update_record(**values)
            newid = None
        else:
            newid = self.insert(**values)
        return newid

    def validate_and_update_or_insert(self, _key=DEFAULT, **fields):
        if _key is DEFAULT or _key == '':
            primary_keys = {}
            for key, value in fields.iteritems():
                if key in self._primarykey:
                    primary_keys[key] = value
            if primary_keys != {}:
                record = self(**primary_keys)
                _key = primary_keys
            else:
                required_keys = {}
                for key, value in fields.iteritems():
                    if getattr(self, key).required:
                        required_keys[key] = value
                record = self(**required_keys)
                _key = required_keys
        elif isinstance(_key, dict):
            record = self(**_key)
        else:
            record = self(_key)

        if record:
            response = self.validate_and_update(_key, **fields)
            primary_keys = {}
            for key in self._primarykey:
                primary_keys[key] = getattr(record, key)
            response.id = primary_keys
        else:
            response = self.validate_and_insert(**fields)
        return response

    def bulk_insert(self, items):
        """
        here items is a list of dictionaries
        """
        items = [self._listify(item) for item in items]
        if any(f(item) for item in items for f in self._before_insert):return 0
        ret = self._db._adapter.bulk_insert(self, items)
        ret and [[f(item, ret[k]) for k, item in enumerate(items)] for f in self._after_insert]
        return ret

    def _truncate(self, mode=None):
        return self._db._adapter._truncate(self, mode)

    def truncate(self, mode=None):
        return self._db._adapter.truncate(self, mode)

    def import_from_csv_file(self,
                             csvfile,
                             id_map=None,
                             null='<NULL>',
                             unique='uuid',
                             id_offset=None,  # id_offset used only when id_map is None
                             *args, **kwargs
                             ):
        """
        Import records from csv file.
        Column headers must have same names as table fields.
        Field 'id' is ignored.
        If column names read 'table.file' the 'table.' prefix is ignored.

        - 'unique' argument is a field which must be unique (typically a
          uuid field)
        - 'restore' argument is default False; if set True will remove old values
          in table first.
        - 'id_map' if set to None will not map ids

        The import will keep the id numbers in the restored table.
        This assumes that there is an field of type id that is integer and in
        incrementing order.
        Will keep the id numbers in restored table.
        """

        delimiter = kwargs.get('delimiter', ',')
        quotechar = kwargs.get('quotechar', '"')
        quoting = kwargs.get('quoting', csv.QUOTE_MINIMAL)
        restore = kwargs.get('restore', False)
        if restore:
            self._db[self].truncate()

        reader = csv.reader(csvfile, delimiter=delimiter,
                            quotechar=quotechar, quoting=quoting)
        colnames = None
        if isinstance(id_map, dict):
            if not self._tablename in id_map:
                id_map[self._tablename] = {}
            id_map_self = id_map[self._tablename]

        def fix(field, value, id_map, id_offset):
            list_reference_s='list:reference'
            if value == null:
                value = None
            elif field.type == 'blob':
                value = base64.b64decode(value)
            elif field.type == 'double' or field.type == 'float':
                if not value.strip():
                    value = None
                else:
                    value = float(value)
            elif field.type in ('integer', 'bigint'):
                if not value.strip():
                    value = None
                else:
                    value = long(value)
            elif field.type.startswith('list:string'):
                value = bar_decode_string(value)
            elif field.type.startswith(list_reference_s):
                ref_table = field.type[len(list_reference_s):].strip()
                if id_map is not None:
                    value = [id_map[ref_table][long(v)]
                             for v in bar_decode_string(value)]
                else:
                    value = [v for v in bar_decode_string(value)]
            elif field.type.startswith('list:'):
                value = bar_decode_integer(value)
            elif id_map and field.type.startswith('reference'):
                try:
                    value = id_map[field.type[9:].strip()][long(value)]
                except KeyError:
                    pass
            elif id_offset and field.type.startswith('reference'):
                try:
                    value = id_offset[field.type[9:].strip()]+long(value)
                except KeyError:
                    pass
            return (field.name, value)

        def is_id(colname):
            if colname in self:
                return self[colname].type == 'id'
            else:
                return False

        first = True
        unique_idx = None
        for lineno, line in enumerate(reader):
            if not line:
                break
            if not colnames:
                # assume this is the first line of the input, contains colnames
                colnames = [x.split('.', 1)[-1] for x in line][:len(line)]
                cols, cid = [], None
                for i, colname in enumerate(colnames):
                    if is_id(colname):
                        cid = i
                    elif colname in self.fields:
                        cols.append((i, self[colname]))
                    if colname == unique:
                        unique_idx = i
            else:
                # every other line contains instead data
                items = []
                for i, field in cols:
                    try:
                        items.append(fix(field, line[i], id_map, id_offset))
                    except ValueError:
                        raise RuntimeError("Unable to parse line:%s field:%s value:'%s'"
                                           % (lineno+1, field, line[i]))

                if not (id_map or cid is None or id_offset is None or unique_idx):
                    csv_id = long(line[cid])
                    curr_id = self.insert(**dict(items))
                    if first:
                        first = False
                        # First curr_id is bigger than csv_id,
                        # then we are not restoring but
                        # extending db table with csv db table
                        id_offset[self._tablename] = (curr_id-csv_id) \
                            if curr_id > csv_id else 0
                    # create new id until we get the same as old_id+offset
                    while curr_id < csv_id+id_offset[self._tablename]:
                        self._db(self._db[self][colnames[cid]] == curr_id).delete()
                        curr_id = self.insert(**dict(items))
                # Validation. Check for duplicate of 'unique' &,
                # if present, update instead of insert.
                elif not unique_idx:
                    new_id = self.insert(**dict(items))
                else:
                    unique_value = line[unique_idx]
                    query = self._db[self][unique] == unique_value
                    record = self._db(query).select().first()
                    if record:
                        record.update_record(**dict(items))
                        new_id = record[self._id.name]
                    else:
                        new_id = self.insert(**dict(items))
                if id_map and cid is not None:
                    id_map_self[long(line[cid])] = new_id

    def as_dict(self, flat=False, sanitize=True):
        table_as_dict = dict(tablename=str(self),
                             fields=[],
                             sequence_name=self._sequence_name,
                             trigger_name=self._trigger_name,
                             common_filter=self._common_filter,
                             format=self._format,
                             singular=self._singular,
                             plural=self._plural)

        for field in self:
            if (field.readable or field.writable) or (not sanitize):
                table_as_dict["fields"].append(field.as_dict(
                    flat=flat, sanitize=sanitize))
        return table_as_dict

    def as_xml(self, sanitize=True):
        if not have_serializers:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return serializers.xml(d)

    def as_json(self, sanitize=True):
        if not have_serializers:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return serializers.json(d)

    def as_yaml(self, sanitize=True):
        if not have_serializers:
            raise ImportError("No YAML serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return serializers.yaml(d)

    def with_alias(self, alias):
        return self._db._adapter.alias(self, alias)

    def on(self, query):
        return Expression(self._db, self._db._adapter.ON, self, query)


def archive_record(qset, fs, archive_table, current_record):
    tablenames = qset.db._adapter.tables(qset.query)
    if len(tablenames) != 1:
        raise RuntimeError("cannot update join")
    for row in qset.select():
        fields = archive_table._filter_fields(row)
        fields[current_record] = row.id
        archive_table.insert(**fields)
    return False


class Expression(object):

    def __init__(self,
                 db,
                 op,
                 first=None,
                 second=None,
                 type=None,
                 **optional_args
                 ):

        self.db = db
        self.op = op
        self.first = first
        self.second = second
        self._table = getattr(first, '_table', None)
        ### self._tablename =  first._tablename ## CHECK
        if not type and first and hasattr(first, 'type'):
            self.type = first.type
        else:
            self.type = type
        self.optional_args = optional_args

    def sum(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'SUM', self.type)

    def max(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'MAX', self.type)

    def min(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'MIN', self.type)

    def len(self):
        db = self.db
        return Expression(db, db._adapter.LENGTH, self, None, 'integer')

    def avg(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'AVG', self.type)

    def abs(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'ABS', self.type)

    def lower(self):
        db = self.db
        return Expression(db, db._adapter.LOWER, self, None, self.type)

    def upper(self):
        db = self.db
        return Expression(db, db._adapter.UPPER, self, None, self.type)

    def replace(self, a, b):
        db = self.db
        return Expression(db, db._adapter.REPLACE, self, (a, b), self.type)

    def year(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'year', 'integer')

    def month(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'month', 'integer')

    def day(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'day', 'integer')

    def hour(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'hour', 'integer')

    def minutes(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'minute', 'integer')

    def coalesce(self, *others):
        db = self.db
        return Expression(db, db._adapter.COALESCE, self, others, self.type)

    def coalesce_zero(self):
        db = self.db
        return Expression(db, db._adapter.COALESCE_ZERO, self, None, self.type)

    def seconds(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'second', 'integer')

    def epoch(self):
        db = self.db
        return Expression(db, db._adapter.EPOCH, self, None, 'integer')

    def __getslice__(self, start, stop):
        db = self.db
        if start < 0:
            pos0 = '(%s - %d)' % (self.len(), abs(start) - 1)
        else:
            pos0 = start + 1

        if stop < 0:
            length = '(%s - %d - %s)' % (self.len(), abs(stop) - 1, pos0)
        elif stop == sys.maxint:
            length = self.len()
        else:
            length = '(%s - %s)' % (stop + 1, pos0)
        return Expression(db, db._adapter.SUBSTRING,
                          self, (pos0, length), self.type)

    def __getitem__(self, i):
        return self[i:i + 1]

    def __str__(self):
        return self.db._adapter.expand(self, self.type)

    def __or__(self, other):  # for use in sortby
        db = self.db
        return Expression(db, db._adapter.COMMA, self, other, self.type)

    def __invert__(self):
        db = self.db
        if hasattr(self, '_op') and self.op == db._adapter.INVERT:
            return self.first
        return Expression(db, db._adapter.INVERT, self, type=self.type)

    def __add__(self, other):
        db = self.db
        return Expression(db, db._adapter.ADD, self, other, self.type)

    def __sub__(self, other):
        db = self.db
        if self.type in ('integer', 'bigint'):
            result_type = 'integer'
        elif self.type in ['date', 'time', 'datetime', 'double', 'float']:
            result_type = 'double'
        elif self.type.startswith('decimal('):
            result_type = self.type
        else:
            raise SyntaxError("subtraction operation not supported for type")
        return Expression(db, db._adapter.SUB, self, other, result_type)

    def __mul__(self, other):
        db = self.db
        return Expression(db, db._adapter.MUL, self, other, self.type)

    def __div__(self, other):
        db = self.db
        return Expression(db, db._adapter.DIV, self, other, self.type)

    def __mod__(self, other):
        db = self.db
        return Expression(db, db._adapter.MOD, self, other, self.type)

    def __eq__(self, value):
        db = self.db
        return Query(db, db._adapter.EQ, self, value)

    def __ne__(self, value):
        db = self.db
        return Query(db, db._adapter.NE, self, value)

    def __lt__(self, value):
        db = self.db
        return Query(db, db._adapter.LT, self, value)

    def __le__(self, value):
        db = self.db
        return Query(db, db._adapter.LE, self, value)

    def __gt__(self, value):
        db = self.db
        return Query(db, db._adapter.GT, self, value)

    def __ge__(self, value):
        db = self.db
        return Query(db, db._adapter.GE, self, value)

    def like(self, value, case_sensitive=False):
        db = self.db
        op = case_sensitive and db._adapter.LIKE or db._adapter.ILIKE
        return Query(db, op, self, value)

    def regexp(self, value):
        db = self.db
        return Query(db, db._adapter.REGEXP, self, value)

    def belongs(self, *value, **kwattr):
        """
        Accepts the following inputs::

           field.belongs(1, 2)
           field.belongs((1, 2))
           field.belongs(query)

        Does NOT accept:

               field.belongs(1)

        If the set you want back includes `None` values, you can do::

            field.belongs((1, None), null=True)

        """
        db = self.db
        if len(value) == 1:
            value = value[0]
        if isinstance(value, Query):
            value = db(value)._select(value.first._table._id)
        elif not isinstance(value, basestring):
            value = set(value)
            if kwattr.get('null') and None in value:
                value.remove(None)
                return (self == None) | Query(db, db._adapter.BELONGS, self, value)
        return Query(db, db._adapter.BELONGS, self, value)

    def startswith(self, value):
        db = self.db
        if not self.type in ('string', 'text', 'json', 'upload'):
            raise SyntaxError("startswith used with incompatible field type")
        return Query(db, db._adapter.STARTSWITH, self, value)

    def endswith(self, value):
        db = self.db
        if not self.type in ('string', 'text', 'json', 'upload'):
            raise SyntaxError("endswith used with incompatible field type")
        return Query(db, db._adapter.ENDSWITH, self, value)

    def contains(self, value, all=False, case_sensitive=False):
        """
        The case_sensitive parameters is only useful for PostgreSQL
        For other RDMBs it is ignored and contains is always case insensitive
        For MongoDB and GAE contains is always case sensitive
        """
        db = self.db
        if isinstance(value, (list, tuple)):
            subqueries = [self.contains(str(v).strip(), case_sensitive=case_sensitive)
                          for v in value if str(v).strip()]
            if not subqueries:
                return self.contains('')
            else:
                return reduce(all and AND or OR, subqueries)
        if not self.type in ('string', 'text', 'json', 'upload') and not self.type.startswith('list:'):
            raise SyntaxError("contains used with incompatible field type")
        return Query(db, db._adapter.CONTAINS, self, value, case_sensitive=case_sensitive)

    def with_alias(self, alias):
        db = self.db
        return Expression(db, db._adapter.AS, self, alias, self.type)

    # GIS expressions

    def st_asgeojson(self, precision=15, options=0, version=1):
        return Expression(self.db, self.db._adapter.ST_ASGEOJSON, self,
                          dict(precision=precision, options=options,
                               version=version), 'string')

    def st_astext(self):
        db = self.db
        return Expression(db, db._adapter.ST_ASTEXT, self, type='string')

    def st_x(self):
        db = self.db
        return Expression(db, db._adapter.ST_X, self, type='string')

    def st_y(self):
        db = self.db
        return Expression(db, db._adapter.ST_Y, self, type='string')

    def st_distance(self, other):
        db = self.db
        return Expression(db, db._adapter.ST_DISTANCE, self, other, 'double')

    def st_simplify(self, value):
        db = self.db
        return Expression(db, db._adapter.ST_SIMPLIFY, self, value, self.type)

    # GIS queries

    def st_contains(self, value):
        db = self.db
        return Query(db, db._adapter.ST_CONTAINS, self, value)

    def st_equals(self, value):
        db = self.db
        return Query(db, db._adapter.ST_EQUALS, self, value)

    def st_intersects(self, value):
        db = self.db
        return Query(db, db._adapter.ST_INTERSECTS, self, value)

    def st_overlaps(self, value):
        db = self.db
        return Query(db, db._adapter.ST_OVERLAPS, self, value)

    def st_touches(self, value):
        db = self.db
        return Query(db, db._adapter.ST_TOUCHES, self, value)

    def st_within(self, value):
        db = self.db
        return Query(db, db._adapter.ST_WITHIN, self, value)

    def st_dwithin(self, value, distance):
        db = self.db
        return Query(db, db._adapter.ST_DWITHIN, self, (value, distance))

    # for use in both Query and sortby


class SQLCustomType(object):
    """
    Allows defining of custom SQL types

    Args:
        type: the web2py type (default = 'string')
        native: the backend type
        encoder: how to encode the value to store it in the backend
        decoder: how to decode the value retrieved from the backend
        validator: what validators to use ( default = None, will use the
            default validator for type)

    Example::
        Define as:

            decimal = SQLCustomType(
                type ='double',
                native ='integer',
                encoder =(lambda x: int(float(x) * 100)),
                decoder = (lambda x: Decimal("0.00") + Decimal(str(float(x)/100)) )
                )

            db.define_table(
                'example',
                Field('value', type=decimal)
                )

    """

    def __init__(self,
                 type='string',
                 native=None,
                 encoder=None,
                 decoder=None,
                 validator=None,
                 _class=None,
                 ):

        self.type = type
        self.native = native
        self.encoder = encoder or (lambda x: x)
        self.decoder = decoder or (lambda x: x)
        self.validator = validator
        self._class = _class or type

    def startswith(self, text=None):
        try:
            return self.type.startswith(self, text)
        except TypeError:
            return False

    def endswith(self, text=None):
        try:
            return self.type.endswith(self, text)
        except TypeError:
            return False

    def __getslice__(self, a=0, b=100):
        return None

    def __getitem__(self, i):
        return None

    def __str__(self):
        return self._class


class FieldVirtual(object):
    def __init__(self, name, f=None, ftype='string', label=None, table_name=None):
        # for backward compatibility
        (self.name, self.f) = (name, f) if f else ('unknown', name)
        self.type = ftype
        self.label = label or self.name.capitalize().replace('_', ' ')
        self.represent = lambda v, r=None:v
        self.formatter = IDENTITY
        self.comment = None
        self.readable = True
        self.writable = False
        self.requires = None
        self.widget = None
        self.tablename = table_name
        self.filter_out = None
    def __str__(self):
        return '%s.%s' % (self.tablename, self.name)


class FieldMethod(object):
    def __init__(self, name, f=None, handler=None):
        # for backward compatibility
        (self.name, self.f) = (name, f) if f else ('unknown', name)
        self.handler = handler


def list_represent(x, r=None):
    return ', '.join(str(y) for y in x or [])


class Field(Expression):

    Virtual = FieldVirtual
    Method = FieldMethod
    Lazy = FieldMethod  # for backward compatibility

    """
    Represents a database field

    Example:
        Usage::

            a = Field(name, 'string', length=32, default=None, required=False,
                requires=IS_NOT_EMPTY(), ondelete='CASCADE',
                notnull=False, unique=False,
                uploadfield=True, widget=None, label=None, comment=None,
                uploadfield=True, # True means store on disk,
                                  # 'a_field_name' means store in this field in db
                                  # False means file content will be discarded.
                writable=True, readable=True, update=None, authorize=None,
                autodelete=False, represent=None, uploadfolder=None,
                uploadseparate=False # upload to separate directories by uuid_keys
                                     # first 2 character and tablename.fieldname
                                     # False - old behavior
                                     # True - put uploaded file in
                                     #   <uploaddir>/<tablename>.<fieldname>/uuid_key[:2]
                                     #        directory)
                uploadfs=None        # a pyfilesystem where to store upload
                )

    to be used as argument of `DAL.define_table`

    """

    def __init__(self,
                 fieldname,
                 type='string',
                 length=None,
                 default=DEFAULT,
                 required=False,
                 requires=DEFAULT,
                 ondelete='CASCADE',
                 notnull=False,
                 unique=False,
                 uploadfield=True,
                 widget=None,
                 label=None,
                 comment=None,
                 writable=True,
                 readable=True,
                 update=None,
                 authorize=None,
                 autodelete=False,
                 represent=None,
                 uploadfolder=None,
                 uploadseparate=False,
                 uploadfs=None,
                 compute=None,
                 custom_store=None,
                 custom_retrieve=None,
                 custom_retrieve_file_properties=None,
                 custom_delete=None,
                 filter_in=None,
                 filter_out=None,
                 custom_qualifier=None,
                 map_none=None,
                 rname=None
                 ):
        self._db = self.db = None  # both for backward compatibility
        self.op = None
        self.first = None
        self.second = None
        if isinstance(fieldname, unicode):
            try:
                fieldname = str(fieldname)
            except UnicodeEncodeError:
                raise SyntaxError('Field: invalid unicode field name')
        self.name = fieldname = cleanup(fieldname)
        if not isinstance(fieldname, str) or hasattr(Table, fieldname) or \
                fieldname[0] == '_' or '.' in fieldname or \
                REGEX_PYTHON_KEYWORDS.match(fieldname):
            raise SyntaxError('Field: invalid field name: %s, '
                              'use rname for "funny" names' % fieldname)

        if not isinstance(type, (Table, Field)):
            self.type = type
        else:
            self.type = 'reference %s' % type

        self.length = length if not length is None else DEFAULTLENGTH.get(self.type, 512)
        self.default = default if default != DEFAULT else (update or None)
        self.required = required  # is this field required
        self.ondelete = ondelete.upper()  # this is for reference fields only
        self.notnull = notnull
        self.unique = unique
        self.uploadfield = uploadfield
        self.uploadfolder = uploadfolder
        self.uploadseparate = uploadseparate
        self.uploadfs = uploadfs
        self.widget = widget
        self.comment = comment
        self.writable = writable
        self.readable = readable
        self.update = update
        self.authorize = authorize
        self.autodelete = autodelete
        self.represent = (list_represent if represent is None and
                          type in ('list:integer', 'list:string') else represent)
        self.compute = compute
        self.isattachment = True
        self.custom_store = custom_store
        self.custom_retrieve = custom_retrieve
        self.custom_retrieve_file_properties = custom_retrieve_file_properties
        self.custom_delete = custom_delete
        self.filter_in = filter_in
        self.filter_out = filter_out
        self.custom_qualifier = custom_qualifier
        self.label = (label if label is not None else
                      fieldname.replace('_', ' ').title())
        self.requires = requires if requires is not None else []
        self.map_none = map_none
        self._rname = rname

    def set_attributes(self, *args, **attributes):
        self.__dict__.update(*args, **attributes)

    def clone(self, point_self_references_to=False, **args):
        field = copy.copy(self)
        if point_self_references_to and \
                field.type == 'reference %s'+field._tablename:
            field.type = 'reference %s' % point_self_references_to
        field.__dict__.update(args)
        return field

    def store(self, file, filename=None, path=None):
        if self.custom_store:
            return self.custom_store(file, filename, path)
        if isinstance(file, cgi.FieldStorage):
            filename = filename or file.filename
            file = file.file
        elif not filename:
            filename = file.name
        filename = os.path.basename(filename.replace('/', os.sep).replace('\\', os.sep))
        m = REGEX_STORE_PATTERN.search(filename)
        extension = m and m.group('e') or 'txt'
        uuid_key = web2py_uuid().replace('-', '')[-16:]
        encoded_filename = base64.b16encode(filename).lower()
        newfilename = '%s.%s.%s.%s' % \
            (self._tablename, self.name, uuid_key, encoded_filename)
        newfilename = newfilename[:(self.length - 1 - len(extension))] + '.' + extension
        self_uploadfield = self.uploadfield
        if isinstance(self_uploadfield, Field):
            blob_uploadfield_name = self_uploadfield.uploadfield
            keys = {self_uploadfield.name: newfilename,
                    blob_uploadfield_name: file.read()}
            self_uploadfield.table.insert(**keys)
        elif self_uploadfield is True:
            if path:
                pass
            elif self.uploadfolder:
                path = self.uploadfolder
            elif self.db._adapter.folder:
                path = pjoin(self.db._adapter.folder, '..', 'uploads')
            else:
                raise RuntimeError(
                    "you must specify a Field(..., uploadfolder=...)")
            if self.uploadseparate:
                if self.uploadfs:
                    raise RuntimeError("not supported")
                path = pjoin(path, "%s.%s" % (
                    self._tablename, self.name), uuid_key[:2]
                )
            if not exists(path):
                os.makedirs(path)
            pathfilename = pjoin(path, newfilename)
            if self.uploadfs:
                dest_file = self.uploadfs.open(newfilename, 'wb')
            else:
                dest_file = open(pathfilename, 'wb')
            try:
                shutil.copyfileobj(file, dest_file)
            except IOError:
                raise IOError(
                    'Unable to store file "%s" because invalid permissions, '
                    'readonly file system, or filename too long' % pathfilename)
            dest_file.close()
        return newfilename

    def retrieve(self, name, path=None, nameonly=False):
        """
        If `nameonly==True` return (filename, fullfilename) instead of
        (filename, stream)
        """
        self_uploadfield = self.uploadfield
        if self.custom_retrieve:
            return self.custom_retrieve(name, path)
        import http
        if self.authorize or isinstance(self_uploadfield, str):
            row = self.db(self == name).select().first()
            if not row:
                raise http.HTTP(404)
        if self.authorize and not self.authorize(row):
            raise http.HTTP(403)
        file_properties = self.retrieve_file_properties(name, path)
        filename = file_properties['filename']
        if isinstance(self_uploadfield, str):  # ## if file is in DB
            stream = StringIO.StringIO(row[self_uploadfield] or '')
        elif isinstance(self_uploadfield, Field):
            blob_uploadfield_name = self_uploadfield.uploadfield
            query = self_uploadfield == name
            data = self_uploadfield.table(query)[blob_uploadfield_name]
            stream = StringIO.StringIO(data)
        elif self.uploadfs:
            # ## if file is on pyfilesystem
            stream = self.uploadfs.open(name, 'rb')
        else:
            # ## if file is on regular filesystem
            # this is intentially a sting with filename and not a stream
            # this propagates and allows stream_file_or_304_or_206 to be called
            fullname = pjoin(file_properties['path'], name)
            if nameonly:
                return (filename, fullname)
            stream = open(fullname, 'rb')
        return (filename, stream)

    def retrieve_file_properties(self, name, path=None):
        m = REGEX_UPLOAD_PATTERN.match(name)
        if not m or not self.isattachment:
            raise TypeError('Can\'t retrieve %s file properties' % name)
        self_uploadfield = self.uploadfield
        if self.custom_retrieve_file_properties:
            return self.custom_retrieve_file_properties(name, path)
        if m.group('name'):
            try:
                filename = base64.b16decode(m.group('name'), True)
                filename = REGEX_CLEANUP_FN.sub('_', filename)
            except (TypeError, AttributeError):
                filename = name
        else:
            filename = name
        # ## if file is in DB
        if isinstance(self_uploadfield, (str, Field)):
            return dict(path=None, filename=filename)
        # ## if file is on filesystem
        if not path:
            if self.uploadfolder:
                path = self.uploadfolder
            else:
                path = pjoin(self.db._adapter.folder, '..', 'uploads')
        if self.uploadseparate:
            t = m.group('table')
            f = m.group('field')
            u = m.group('uuidkey')
            path = pjoin(path, "%s.%s" % (t, f), u[:2])
        return dict(path=path, filename=filename)

    def formatter(self, value):
        requires = self.requires
        if value is None or not requires:
            return value or self.map_none
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        elif isinstance(requires, tuple):
            requires = list(requires)
        else:
            requires = copy.copy(requires)
        requires.reverse()
        for item in requires:
            if hasattr(item, 'formatter'):
                value = item.formatter(value)
        return value

    def validate(self, value):
        if not self.requires or self.requires == DEFAULT:
            return ((value if value != self.map_none else None), None)
        requires = self.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        for validator in requires:
            (value, error) = validator(value)
            if error:
                return (value, error)
        return ((value if value != self.map_none else None), None)

    def count(self, distinct=None):
        return Expression(self.db, self.db._adapter.COUNT, self, distinct, 'integer')

    def as_dict(self, flat=False, sanitize=True):
        attrs = ('name', 'authorize', 'represent', 'ondelete',
                 'custom_store', 'autodelete', 'custom_retrieve',
                 'filter_out', 'uploadseparate', 'widget', 'uploadfs',
                 'update', 'custom_delete', 'uploadfield', 'uploadfolder',
                 'custom_qualifier', 'unique', 'writable', 'compute',
                 'map_none', 'default', 'type', 'required', 'readable',
                 'requires', 'comment', 'label', 'length', 'notnull',
                 'custom_retrieve_file_properties', 'filter_in')
        serializable = (int, long, basestring, float, tuple,
                        bool, type(None))

        def flatten(obj):
            if isinstance(obj, dict):
                return dict((flatten(k), flatten(v)) for k, v in obj.items())
            elif isinstance(obj, (tuple, list, set)):
                return [flatten(v) for v in obj]
            elif isinstance(obj, serializable):
                return obj
            elif isinstance(obj, (datetime.datetime,
                                  datetime.date, datetime.time)):
                return str(obj)
            else:
                return None

        d = dict()
        if not (sanitize and not (self.readable or self.writable)):
            for attr in attrs:
                if flat:
                    d.update({attr: flatten(getattr(self, attr))})
                else:
                    d.update({attr: getattr(self, attr)})
            d["fieldname"] = d.pop("name")
        return d

    def as_xml(self, sanitize=True):
        if have_serializers:
            xml = serializers.xml
        else:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return xml(d)

    def as_json(self, sanitize=True):
        if have_serializers:
            json = serializers.json
        else:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return json(d)

    def as_yaml(self, sanitize=True):
        if have_serializers:
            d = self.as_dict(flat=True, sanitize=sanitize)
            return serializers.yaml(d)
        else:
            raise ImportError("No YAML serializers available")

    def __nonzero__(self):
        return True

    def __str__(self):
        try:
            return '%s.%s' % (self.tablename, self.name)
        except:
            return '<no table>.%s' % self.name

    @property
    def sqlsafe(self):
        if self._table:
            return self._table.sqlsafe + '.' + \
                (self._rname or self._db._adapter.sqlsafe_field(self.name))
        return '<no table>.%s' % self.name

    @property
    def sqlsafe_name(self):
        return self._rname or self._db._adapter.sqlsafe_field(self.name)


class Query(object):

    """
    Necessary to define a set.
    It can be stored or can be passed to `DAL.__call__()` to obtain a `Set`

    Example:
        Use as::

            query = db.users.name=='Max'
            set = db(query)
            records = set.select()

    """

    def __init__(self,
                 db,
                 op,
                 first=None,
                 second=None,
                 ignore_common_filters=False,
                 **optional_args
                 ):
        self.db = self._db = db
        self.op = op
        self.first = first
        self.second = second
        self.ignore_common_filters = ignore_common_filters
        self.optional_args = optional_args

    def __repr__(self):
        return '<Query %s>' % BaseAdapter.expand(self.db._adapter, self)

    def __str__(self):
        return str(self.db._adapter.expand(self))

    def __and__(self, other):
        return Query(self.db, self.db._adapter.AND, self, other)

    __rand__ = __and__

    def __or__(self, other):
        return Query(self.db, self.db._adapter.OR, self, other)

    __ror__ = __or__

    def __invert__(self):
        if self.op==self.db._adapter.NOT:
            return self.first
        return Query(self.db, self.db._adapter.NOT, self)

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __ne__(self, other):
        return not (self == other)

    def case(self, t=1, f=0):
        return self.db._adapter.CASE(self, t, f)

    def as_dict(self, flat=False, sanitize=True):
        """Experimental stuff

        This allows to return a plain dictionary with the basic
        query representation. Can be used with json/xml services
        for client-side db I/O

        Example:
            Usage::

                q = db.auth_user.id != 0
                q.as_dict(flat=True)
                {
                "op": "NE",
                "first":{
                    "tablename": "auth_user",
                    "fieldname": "id"
                    },
                "second":0
                }
        """

        SERIALIZABLE_TYPES = (tuple, dict, set, list, int, long, float,
                              basestring, type(None), bool)

        def loop(d):
            newd = dict()
            for k, v in d.items():
                if k in ("first", "second"):
                    if isinstance(v, self.__class__):
                        newd[k] = loop(v.__dict__)
                    elif isinstance(v, Field):
                        newd[k] = {"tablename": v._tablename,
                                   "fieldname": v.name}
                    elif isinstance(v, Expression):
                        newd[k] = loop(v.__dict__)
                    elif isinstance(v, SERIALIZABLE_TYPES):
                        newd[k] = v
                    elif isinstance(v, (datetime.date,
                                        datetime.time,
                                        datetime.datetime)):
                        newd[k] = unicode(v)
                elif k == "op":
                    if callable(v):
                        newd[k] = v.__name__
                    elif isinstance(v, basestring):
                        newd[k] = v
                    else: pass  # not callable or string
                elif isinstance(v, SERIALIZABLE_TYPES):
                    if isinstance(v, dict):
                        newd[k] = loop(v)
                    else: newd[k] = v
            return newd

        if flat:
            return loop(self.__dict__)
        else: return self.__dict__

    def as_xml(self, sanitize=True):
        if have_serializers:
            xml = serializers.xml
        else:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return xml(d)

    def as_json(self, sanitize=True):
        if have_serializers:
            json = serializers.json
        else:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return json(d)


def xorify(orderby):
    if not orderby:
        return None
    orderby2 = orderby[0]
    for item in orderby[1:]:
        orderby2 = orderby2 | item
    return orderby2


def use_common_filters(query):
    return (query and hasattr(query, 'ignore_common_filters') and \
                not query.ignore_common_filters)


class Set(object):

    """
    Represents a set of records in the database.
    Records are identified by the `query=Query(...)` object.
    Normally the Set is generated by `DAL.__call__(Query(...))`

    Given a set, for example::

        myset = db(db.users.name=='Max')

    you can::

        myset.update(db.users.name='Massimo')
        myset.delete() # all elements in the set
        myset.select(orderby=db.users.id, groupby=db.users.name, limitby=(0, 10))

    and take subsets:

       subset = myset(db.users.id<5)

    """

    def __init__(self, db, query, ignore_common_filters = None):
        self.db = db
        self._db = db  # for backward compatibility
        self.dquery = None

        # if query is a dict, parse it
        if isinstance(query, dict):
            query = self.parse(query)

        if not ignore_common_filters is None and \
                use_common_filters(query) == ignore_common_filters:
            query = copy.copy(query)
            query.ignore_common_filters = ignore_common_filters
        self.query = query

    def __repr__(self):
        return '<Set %s>' % BaseAdapter.expand(self.db._adapter, self.query)

    def __call__(self, query, ignore_common_filters=False):
        if query is None:
            return self
        elif isinstance(query, Table):
            query = self.db._adapter.id_query(query)
        elif isinstance(query, str):
            query = Expression(self.db, query)
        elif isinstance(query, Field):
            query = query!=None
        if self.query:
            return Set(self.db, self.query & query,
                       ignore_common_filters=ignore_common_filters)
        else:
            return Set(self.db, query,
                       ignore_common_filters=ignore_common_filters)

    def _count(self, distinct=None):
        return self.db._adapter._count(self.query, distinct)

    def _select(self, *fields, **attributes):
        adapter = self.db._adapter
        tablenames = adapter.tables(self.query,
                                    attributes.get('join', None),
                                    attributes.get('left', None),
                                    attributes.get('orderby', None),
                                    attributes.get('groupby', None))
        fields = adapter.expand_all(fields, tablenames)
        return adapter._select(self.query, fields, attributes)

    def _delete(self):
        db = self.db
        tablename = db._adapter.get_table(self.query)
        return db._adapter._delete(tablename, self.query)

    def _update(self, **update_fields):
        db = self.db
        tablename = db._adapter.get_table(self.query)
        fields = db[tablename]._listify(update_fields, update=True)
        return db._adapter._update(tablename, self.query, fields)

    def as_dict(self, flat=False, sanitize=True):
        if flat:
            uid = dbname = uri = None
            codec = self.db._db_codec
            if not sanitize:
                uri, dbname, uid = (self.db._dbname, str(self.db),
                                    self.db._db_uid)
            d = {"query": self.query.as_dict(flat=flat)}
            d["db"] = {"uid": uid, "codec": codec,
                       "name": dbname, "uri": uri}
            return d
        else: return self.__dict__

    def as_xml(self, sanitize=True):
        if have_serializers:
            xml = serializers.xml
        else:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return xml(d)

    def as_json(self, sanitize=True):
        if have_serializers:
            json = serializers.json
        else:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return json(d)

    def parse(self, dquery):
        """Experimental: Turn a dictionary into a Query object"""
        self.dquery = dquery
        return self.build(self.dquery)

    def build(self, d):
        """Experimental: see .parse()"""
        op, first, second = (d["op"], d["first"],
                             d.get("second", None))
        left = right = built = None

        if op in ("AND", "OR"):
            if not (type(first), type(second)) == (dict, dict):
                raise SyntaxError("Invalid AND/OR query")
            if op == "AND":
                built = self.build(first) & self.build(second)
            else: built = self.build(first) | self.build(second)

        elif op == "NOT":
            if first is None:
                raise SyntaxError("Invalid NOT query")
            built = ~self.build(first)
        else:
            # normal operation (GT, EQ, LT, ...)
            for k, v in {"left": first, "right": second}.items():
                if isinstance(v, dict) and v.get("op"):
                    v = self.build(v)
                if isinstance(v, dict) and ("tablename" in v):
                    v = self.db[v["tablename"]][v["fieldname"]]
                if k == "left": left = v
                else: right = v

            if hasattr(self.db._adapter, op):
                opm = getattr(self.db._adapter, op)

            if op == "EQ": built = left == right
            elif op == "NE": built = left != right
            elif op == "GT": built = left > right
            elif op == "GE": built = left >= right
            elif op == "LT": built = left < right
            elif op == "LE": built = left <= right
            elif op in ("JOIN", "LEFT_JOIN", "RANDOM", "ALLOW_NULL"):
                built = Expression(self.db, opm)
            elif op in ("LOWER", "UPPER", "EPOCH", "PRIMARY_KEY",
                        "COALESCE_ZERO", "RAW", "INVERT"):
                built = Expression(self.db, opm, left)
            elif op in ("COUNT", "EXTRACT", "AGGREGATE", "SUBSTRING",
                        "REGEXP", "LIKE", "ILIKE", "STARTSWITH",
                        "ENDSWITH", "ADD", "SUB", "MUL", "DIV",
                        "MOD", "AS", "ON", "COMMA", "NOT_NULL",
                        "COALESCE", "CONTAINS", "BELONGS"):
                built = Expression(self.db, opm, left, right)
            # expression as string
            elif not (left or right): built = Expression(self.db, op)
            else:
                raise SyntaxError("Operator not supported: %s" % op)

        return built

    def isempty(self):
        return not self.select(limitby=(0, 1), orderby_on_limitby=False)

    def count(self, distinct=None, cache=None):
        db = self.db
        if cache:
            cache_model, time_expire = cache
            sql = self._count(distinct=distinct)
            key = db._uri + '/' + sql
            if len(key) > 200: key = hashlib_md5(key).hexdigest()
            return cache_model(
                key,
                (lambda self=self, distinct=distinct:
                 db._adapter.count(self.query, distinct)),
                time_expire)
        return db._adapter.count(self.query, distinct)

    def select(self, *fields, **attributes):
        adapter = self.db._adapter
        tablenames = adapter.tables(self.query,
                                    attributes.get('join', None),
                                    attributes.get('left', None),
                                    attributes.get('orderby', None),
                                    attributes.get('groupby', None))
        fields = adapter.expand_all(fields, tablenames)
        return adapter.select(self.query, fields, attributes)

    def nested_select(self, *fields, **attributes):
        return Expression(self.db, self._select(*fields, **attributes))

    def delete(self):
        db = self.db
        tablename = db._adapter.get_table(self.query)
        table = db[tablename]
        if any(f(self) for f in table._before_delete): return 0
        ret = db._adapter.delete(tablename, self.query)
        ret and [f(self) for f in table._after_delete]
        return ret

    def update(self, **update_fields):
        db = self.db
        tablename = db._adapter.get_table(self.query)
        table = db[tablename]
        table._attempt_upload(update_fields)
        if any(f(self, update_fields) for f in table._before_update):
            return 0
        fields = table._listify(update_fields, update=True)
        if not fields:
            raise SyntaxError("No fields to update")
        ret = db._adapter.update("%s" % table._tablename, self.query, fields)
        ret and [f(self, update_fields) for f in table._after_update]
        return ret

    def update_naive(self, **update_fields):
        """
        Same as update but does not call table._before_update and _after_update
        """
        tablename = self.db._adapter.get_table(self.query)
        table = self.db[tablename]
        fields = table._listify(update_fields, update=True)
        if not fields: raise SyntaxError("No fields to update")

        ret = self.db._adapter.update("%s" % table, self.query, fields)
        return ret

    def validate_and_update(self, **update_fields):
        tablename = self.db._adapter.get_table(self.query)
        response = Row()
        response.errors = Row()
        new_fields = copy.copy(update_fields)
        for key, value in update_fields.iteritems():
            value, error = self.db[tablename][key].validate(value)
            if error:
                response.errors[key] = '%s' % error
            else:
                new_fields[key] = value
        table = self.db[tablename]
        if response.errors:
            response.updated = None
        else:
            if not any(f(self, new_fields) for f in table._before_update):
                fields = table._listify(new_fields, update=True)
                if not fields: raise SyntaxError("No fields to update")
                ret = self.db._adapter.update(tablename, self.query, fields)
                ret and [f(self, new_fields) for f in table._after_update]
            else:
                ret = 0
            response.updated = ret
        return response

    def delete_uploaded_files(self, upload_fields=None):
        table = self.db[self.db._adapter.tables(self.query)[0]]
        # ## mind uploadfield==True means file is not in DB
        if upload_fields:
            fields = upload_fields.keys()
        else:
            fields = table.fields
        fields = [f for f in fields if table[f].type == 'upload'
                   and table[f].uploadfield == True
                   and table[f].autodelete]
        if not fields:
            return False
        for record in self.select(*[table[f] for f in fields]):
            for fieldname in fields:
                field = table[fieldname]
                oldname = record.get(fieldname, None)
                if not oldname:
                    continue
                if upload_fields and oldname == upload_fields[fieldname]:
                    continue
                if field.custom_delete:
                    field.custom_delete(oldname)
                else:
                    uploadfolder = field.uploadfolder
                    if not uploadfolder:
                        uploadfolder = pjoin(
                            self.db._adapter.folder, '..', 'uploads')
                    if field.uploadseparate:
                        items = oldname.split('.')
                        uploadfolder = pjoin(
                            uploadfolder,
                            "%s.%s" % (items[0], items[1]),
                            items[2][:2])
                    oldpath = pjoin(uploadfolder, oldname)
                    if exists(oldpath):
                        os.unlink(oldpath)
        return False


class RecordUpdater(object):
    def __init__(self, colset, table, id):
        self.colset, self.db, self.tablename, self.id = \
            colset, table._db, table._tablename, id

    def __call__(self, **fields):
        colset, db, tablename, id = self.colset, self.db, self.tablename, self.id
        table = db[tablename]
        newfields = fields or dict(colset)
        for fieldname in newfields.keys():
            if not fieldname in table.fields or table[fieldname].type=='id':
                del newfields[fieldname]
        table._db(table._id==id, ignore_common_filters=True).update(**newfields)
        colset.update(newfields)
        return colset


class RecordDeleter(object):

    def __init__(self, table, id):
        self.db, self.tablename, self.id = table._db, table._tablename, id

    def __call__(self):
        return self.db(self.db[self.tablename]._id==self.id).delete()


class LazyReferenceGetter(object):

    def __init__(self, table, id):
        self.db, self.tablename, self.id = table._db, table._tablename, id

    def __call__(self, other_tablename):
        if self.db._lazy_tables is False:
            raise AttributeError()
        table = self.db[self.tablename]
        other_table = self.db[other_tablename]
        for rfield in table._referenced_by:
            if rfield.table == other_table:
                return LazySet(rfield, self.id)

        raise AttributeError()


class LazySet(object):

    def __init__(self, field, id):
        self.db, self.tablename, self.fieldname, self.id = \
            field.db, field._tablename, field.name, id

    def _getset(self):
        query = self.db[self.tablename][self.fieldname]==self.id
        return Set(self.db, query)

    def __repr__(self):
        return repr(self._getset())

    def __call__(self, query, ignore_common_filters=False):
        return self._getset()(query, ignore_common_filters)

    def _count(self, distinct=None):
        return self._getset()._count(distinct)

    def _select(self, *fields, **attributes):
        return self._getset()._select(*fields, **attributes)

    def _delete(self):
        return self._getset()._delete()

    def _update(self, **update_fields):
        return self._getset()._update(**update_fields)

    def isempty(self):
        return self._getset().isempty()

    def count(self, distinct=None, cache=None):
        return self._getset().count(distinct, cache)

    def select(self, *fields, **attributes):
        return self._getset().select(*fields, **attributes)

    def nested_select(self, *fields, **attributes):
        return self._getset().nested_select(*fields, **attributes)

    def delete(self):
        return self._getset().delete()

    def update(self, **update_fields):
        return self._getset().update(**update_fields)

    def update_naive(self, **update_fields):
        return self._getset().update_naive(**update_fields)

    def validate_and_update(self, **update_fields):
        return self._getset().validate_and_update(**update_fields)

    def delete_uploaded_files(self, upload_fields=None):
        return self._getset().delete_uploaded_files(upload_fields)


class VirtualCommand(object):
    def __init__(self, method, row):
        self.method=method
        self.row=row
    def __call__(self, *args, **kwargs):
        return self.method(self.row, *args, **kwargs)


def lazy_virtualfield(f):
    f.__lazy__ = True
    return f


class Rows(object):

    """
    A wrapper for the return value of a select. It basically represents a table.
    It has an iterator and each row is represented as a `Row` dictionary.
    """

    # ## TODO: this class still needs some work to care for ID/OID

    def __init__(self,
                 db=None,
                 records=[],
                 colnames=[],
                 compact=True,
                 rawrows=None
                 ):
        self.db = db
        self.records = records
        self.colnames = colnames
        self.compact = compact
        self.response = rawrows

    def __repr__(self):
        return '<Rows (%s)>' % len(self.records)

    def setvirtualfields(self, **keyed_virtualfields):
        """
        For reference::

            db.define_table('x', Field('number', 'integer'))
            if db(db.x).isempty(): [db.x.insert(number=i) for i in range(10)]

            from gluon.dal import lazy_virtualfield

            class MyVirtualFields(object):
                # normal virtual field (backward compatible, discouraged)
                def normal_shift(self): return self.x.number+1
                # lazy virtual field (because of @staticmethod)
                @lazy_virtualfield
                def lazy_shift(instance, row, delta=4): return row.x.number+delta
            db.x.virtualfields.append(MyVirtualFields())

            for row in db(db.x).select():
                print row.number, row.normal_shift, row.lazy_shift(delta=7)

        """
        if not keyed_virtualfields:
            return self
        for row in self.records:
            for (tablename, virtualfields) in keyed_virtualfields.iteritems():
                attributes = dir(virtualfields)
                if not tablename in row:
                    box = row[tablename] = Row()
                else:
                    box = row[tablename]
                updated = False
                for attribute in attributes:
                    if attribute[0] != '_':
                        method = getattr(virtualfields, attribute)
                        if hasattr(method, '__lazy__'):
                            box[attribute]=VirtualCommand(method, row)
                        elif type(method)==types.MethodType:
                            if not updated:
                                virtualfields.__dict__.update(row)
                                updated = True
                            box[attribute]=method()
        return self

    def __and__(self, other):
        if self.colnames!=other.colnames:
            raise Exception('Cannot & incompatible Rows objects')
        records = self.records+other.records
        return Rows(self.db, records, self.colnames,
                    compact=self.compact or other.compact)

    def __or__(self, other):
        if self.colnames!=other.colnames:
            raise Exception('Cannot | incompatible Rows objects')
        records = [record for record in other.records
                   if not record in self.records]
        records = self.records + records
        return Rows(self.db, records, self.colnames,
                    compact=self.compact or other.compact)

    def __nonzero__(self):
        if len(self.records):
            return 1
        return 0

    def __len__(self):
        return len(self.records)

    def __getslice__(self, a, b):
        return Rows(self.db, self.records[a:b], self.colnames, compact=self.compact)

    def __getitem__(self, i):
        row = self.records[i]
        keys = row.keys()
        if self.compact and len(keys) == 1 and keys[0] != '_extra':
            return row[row.keys()[0]]
        return row

    def __iter__(self):
        """
        Iterator over records
        """

        for i in xrange(len(self)):
            yield self[i]

    def __str__(self):
        """
        Serializes the table into a csv file
        """

        s = StringIO.StringIO()
        self.export_to_csv_file(s)
        return s.getvalue()

    def column(self, column=None):
        return [r[str(column) if column else self.colnames[0]] for r in self]

    def first(self):
        if not self.records:
            return None
        return self[0]

    def last(self):
        if not self.records:
            return None
        return self[-1]

    def find(self, f, limitby=None):
        """
        Returns a new Rows object, a subset of the original object,
        filtered by the function `f`
        """
        if not self:
            return Rows(self.db, [], self.colnames, compact=self.compact)
        records = []
        if limitby:
            a, b = limitby
        else:
            a, b = 0, len(self)
        k = 0
        for i, row in enumerate(self):
            if f(row):
                if a<=k: records.append(self.records[i])
                k += 1
                if k==b: break
        return Rows(self.db, records, self.colnames, compact=self.compact)

    def exclude(self, f):
        """
        Removes elements from the calling Rows object, filtered by the function
        `f`, and returns a new Rows object containing the removed elements
        """
        if not self.records:
            return Rows(self.db, [], self.colnames, compact=self.compact)
        removed = []
        i = 0
        while i < len(self):
            row = self[i]
            if f(row):
                removed.append(self.records[i])
                del self.records[i]
            else:
                i += 1
        return Rows(self.db, removed, self.colnames, compact=self.compact)

    def sort(self, f, reverse=False):
        """
        Returns a list of sorted elements (not sorted in place)
        """
        rows = Rows(self.db, [], self.colnames, compact=self.compact)
        # When compact=True, iterating over self modifies each record,
        # so when sorting self, it is necessary to return a sorted
        # version of self.records rather than the sorted self directly.
        rows.records = [r for (r, s) in sorted(zip(self.records, self),
                                               key=lambda r: f(r[1]),
                                               reverse=reverse)]
        return rows

    def group_by_value(self, *fields, **args):
        """
        Regroups the rows, by one of the fields
        """
        one_result = False
        if 'one_result' in args:
            one_result = args['one_result']

        def build_fields_struct(row, fields, num, groups):
            """ helper function:
            """
            if num > len(fields)-1:
                if one_result:
                    return row
                else:
                    return [row]

            key = fields[num]
            value = row[key]

            if value not in groups:
                groups[value] = build_fields_struct(row, fields, num+1, {})
            else:
                struct = build_fields_struct(row, fields, num+1, groups[ value ])

                # still have more grouping to do
                if type(struct) == type(dict()):
                    groups[value].update()
                # no more grouping, first only is off
                elif type(struct) == type(list()):
                    groups[value] += struct
                # no more grouping, first only on
                else:
                    groups[value] = struct

            return groups

        if len(fields) == 0:
            return self

        # if select returned no results
        if not self.records:
            return {}

        grouped_row_group = dict()

        # build the struct
        for row in self:
            build_fields_struct(row, fields, 0, grouped_row_group)

        return grouped_row_group

    def render(self, i=None, fields=None):
        """
        Takes an index and returns a copy of the indexed row with values
        transformed via the "represent" attributes of the associated fields.

        Args:
            i: index. If not specified, a generator is returned for iteration
                over all the rows.
            fields: a list of fields to transform (if None, all fields with
                "represent" attributes will be transformed)
        """

        if i is None:
            return (self.render(i, fields=fields) for i in range(len(self)))
        import sqlhtml
        row = copy.deepcopy(self.records[i])
        keys = row.keys()
        tables = [f.tablename for f in fields] if fields \
            else [k for k in keys if k != '_extra']
        for table in tables:
            repr_fields = [f.name for f in fields if f.tablename == table] \
                if fields else [k for k in row[table].keys()
                                if (hasattr(self.db[table], k) and
                                    isinstance(self.db[table][k], Field)
                                    and self.db[table][k].represent)]
            for field in repr_fields:
                row[table][field] = sqlhtml.represent(
                    self.db[table][field], row[table][field], row[table])
        if self.compact and len(keys) == 1 and keys[0] != '_extra':
            return row[keys[0]]
        return row

    def as_list(self,
                compact=True,
                storage_to_dict=True,
                datetime_to_str=False,
                custom_types=None):
        """
        Returns the data as a list or dictionary.

        Args:
            storage_to_dict: when True returns a dict, otherwise a list
            datetime_to_str: convert datetime fields as strings
        """
        (oc, self.compact) = (self.compact, compact)
        if storage_to_dict:
            items = [item.as_dict(datetime_to_str, custom_types) for item in self]
        else:
            items = [item for item in self]
        self.compact = compact
        return items

    def as_dict(self,
                key='id',
                compact=True,
                storage_to_dict=True,
                datetime_to_str=False,
                custom_types=None):
        """
        Returns the data as a dictionary of dictionaries (storage_to_dict=True)
        or records (False)

        Args:
            key: the name of the field to be used as dict key, normally the id
            compact: ? (default True)
            storage_to_dict: when True returns a dict, otherwise a list(default True)
            datetime_to_str: convert datetime fields as strings (default False)
        """

        # test for multiple rows
        multi = False
        f = self.first()
        if f and isinstance(key, basestring):
            multi = any([isinstance(v, f.__class__) for v in f.values()])
            if (not "." in key) and multi:
                # No key provided, default to int indices
                def new_key():
                    i = 0
                    while True:
                        yield i
                        i += 1
                key_generator = new_key()
                key = lambda r: key_generator.next()

        rows = self.as_list(compact, storage_to_dict, datetime_to_str, custom_types)
        if isinstance(key, str) and key.count('.')==1:
            (table, field) = key.split('.')
            return dict([(r[table][field], r) for r in rows])
        elif isinstance(key, str):
            return dict([(r[key], r) for r in rows])
        else:
            return dict([(key(r), r) for r in rows])

    def as_trees(self, parent_name='parent_id', children_name='children'):
        roots = []
        drows = {}
        for row in self:
            drows[row.id] = row
            row[children_name] = []
        for row in self:
            parent = row[parent_name]
            if parent is None:
                roots.append(row)
            else:
                drows[parent][children_name].append(row)
        return roots

    def export_to_csv_file(self, ofile, null='<NULL>', *args, **kwargs):
        """
        Exports data to csv, the first line contains the column names

        Args:
            ofile: where the csv must be exported to
            null: how null values must be represented (default '<NULL>')
            delimiter: delimiter to separate values (default ',')
            quotechar: character to use to quote string values (default '"')
            quoting: quote system, use csv.QUOTE_*** (default csv.QUOTE_MINIMAL)
            represent: use the fields .represent value (default False)
            colnames: list of column names to use (default self.colnames)

        This will only work when exporting rows objects!!!!
        DO NOT use this with db.export_to_csv()
        """
        delimiter = kwargs.get('delimiter', ',')
        quotechar = kwargs.get('quotechar', '"')
        quoting = kwargs.get('quoting', csv.QUOTE_MINIMAL)
        represent = kwargs.get('represent', False)
        writer = csv.writer(ofile, delimiter=delimiter,
                            quotechar=quotechar, quoting=quoting)

        def unquote_colnames(colnames):
            unq_colnames = []
            for col in colnames:
                m = self.db._adapter.REGEX_TABLE_DOT_FIELD.match(col)
                if not m:
                    unq_colnames.append(col)
                else:
                    unq_colnames.append('.'.join(m.groups()))
            return unq_colnames

        colnames = kwargs.get('colnames', self.colnames)
        write_colnames = kwargs.get('write_colnames', True)
        # a proper csv starting with the column names
        if write_colnames:
            writer.writerow(unquote_colnames(colnames))

        def none_exception(value):
            """
            Returns a cleaned up value that can be used for csv export:

            - unicode text is encoded as such
            - None values are replaced with the given representation (default <NULL>)
            """
            if value is None:
                return null
            elif isinstance(value, unicode):
                return value.encode('utf8')
            elif isinstance(value, Reference):
                return long(value)
            elif hasattr(value, 'isoformat'):
                return value.isoformat()[:19].replace('T', ' ')
            elif isinstance(value, (list, tuple)):  # for type='list:..'
                return bar_encode(value)
            return value

        for record in self:
            row = []
            for col in colnames:
                m = self.db._adapter.REGEX_TABLE_DOT_FIELD.match(col)
                if not m:
                    row.append(record._extra[col])
                else:
                    (t, f) = m.groups()
                    field = self.db[t][f]
                    if isinstance(record.get(t, None), (Row, dict)):
                        value = record[t][f]
                    else:
                        value = record[f]
                    if field.type=='blob' and not value is None:
                        value = base64.b64encode(value)
                    elif represent and field.represent:
                        value = field.represent(value, record)
                    row.append(none_exception(value))
            writer.writerow(row)

    def xml(self, strict=False, row_name='row', rows_name='rows'):
        """
        Serializes the table using sqlhtml.SQLTABLE (if present)
        """

        if strict:
            return '<%s>\n%s\n</%s>' % (rows_name,
                '\n'.join(row.as_xml(row_name=row_name,
                                     colnames=self.colnames) for
                          row in self), rows_name)

        import sqlhtml
        return sqlhtml.SQLTABLE(self).xml()

    def as_xml(self, row_name='row', rows_name='rows'):
        return self.xml(strict=True, row_name=row_name, rows_name=rows_name)

    def as_json(self, mode='object', default=None):
        """
        Serializes the rows to a JSON list or object with objects
        mode='object' is not implemented (should return a nested
        object structure)
        """

        items = [record.as_json(mode=mode, default=default,
                                serialize=False,
                                colnames=self.colnames) for
                 record in self]

        if have_serializers:
            return serializers.json(items,
                                    default=default or
                                    serializers.custom_json)
        elif simplejson:
            return simplejson.dumps(items)
        else:
            raise RuntimeError("missing simplejson")

    # for consistent naming yet backwards compatible
    as_csv = __str__
    json = as_json

################################################################################
# Geodal utils
################################################################################

def geoPoint(x, y):
    return "POINT (%f %f)" % (x, y)


def geoLine(*line):
    return "LINESTRING (%s)" % ','.join("%f %f" % item for item in line)


def geoPolygon(*line):
    return "POLYGON ((%s))" % ','.join("%f %f" % item for item in line)

################################################################################
# run tests
################################################################################

if __name__ == '__main__':
    import doctest
    doctest.testmod()

from collections import namedtuple
from multiprocessing import Queue
from pathlib import Path
import queue
import os
import datetime

PROGRAM_NAME = "fdbtracer"
_overridenDumpDbPath = None


class EOFReached(Exception):
    pass


# ************************* Message/Error objects *********************
class TracerMessage:
    def __init__(self, text):
        self.text = text
        self.iserror = False


class TracerError:
    def __init__(self, source, error):
        self.text = str(error)
        self.source = source
        self.iserror = True


# ************************* System Parameters *************************
_SysParameters = namedtuple('SysParameters', 'testMode logPath logLevel consoleDebug maxErrors')
_sysParams = None


def initCommonParams(testMode, logPath, logLevel, consoleDebug, maxErrors):
    global _sysParams
    if _sysParams:
        raise Exception('sysParams cannot be initialized twice')
    _sysParams = _SysParameters(testMode, logPath, logLevel, consoleDebug, maxErrors)


def common():
    return _sysParams


# ************************* Traced DB Parameters *************************
_TraceParameters = namedtuple('_TraceParameters', 'host login password traceConf')
_traceParameters = None


def initTraceParams(host, login, password, traceConf):
    global _traceParameters
    if _traceParameters:
        raise Exception('traceParams cannot be initialized twice')
    conf = ''
    traceConfFile = Path(os.getcwd()) / traceConf
    with traceConfFile.open() as f:
        conf = f.read()
    _traceParameters = _TraceParameters(host, login, password, conf)


def trace():
    return _traceParameters


# ************************* Dump DB Parameters *************************
_DB_SUBDIR = 'db'
_CREATEDB_SCRIPT = 'create_db.sql'
_DumpParameters = namedtuple('_DumpParameters', 'databasePath databaseName addDateToName')
_dumpParameters = None


def initDumpParams(databasePath, databaseName, addDateToName):
    global _dumpParameters
    if _dumpParameters:
        raise Exception('dumpParams cannot be initialized twice')
    _dumpParameters = _DumpParameters(databasePath, databaseName, addDateToName)


def dump():
    return _dumpParameters


def overrideDumpDbPath(dbpath):
    global _overridenDumpDbPath
    _overridenDumpDbPath = dbpath


def absDumpDbPath():
    if _overridenDumpDbPath:
        dbPath = _overridenDumpDbPath
    else:
        dbFilename = ''
        if dump().addDateToName:
            dbFilename = '{}-{}.fdb'.format(dump().databaseName, datetime.date.today().isoformat())
        else:
            dbFilename = '{}.fdb'.format(dump().databaseName)
        dbPath = os.path.join(dump().databasePath, dbFilename)
    if not os.path.isabs(dbPath):
        dbPath = os.path.join(os.getcwd(), _DB_SUBDIR, dbPath)
    return dbPath


def absDumpDbScriptPath():
    return os.path.join(os.getcwd(), _DB_SUBDIR, _CREATEDB_SCRIPT)


# ************************* Communicator *************************
class Communicator:
    def __init__(self, *, datastore=None, stop=None, messages=None):
        self._stop = stop if stop else Queue()
        self._datastore = datastore if datastore else Queue()
        self._datastoreInitialized = self._datastore and not isinstance(self._datastore, str)
        self._messages = messages if messages else Queue()

    def stop(self):
        self._stop.put(True)
        self._stop.put(True)
        self._stop.put(True)

    def stopped(self):
        try:
            val = self._stop.get(block=False)
            return val
        except queue.Empty:
            return False

    def pushLine(self,  line):
        if hasattr(self._datastore, 'put'):
            try:
                self._datastore.put(line, block=False)
            except queue.Full:
                return False
            else:
                return True
        return False

    def popLine(self):
        if not self._datastoreInitialized and isinstance(self._datastore, str):
            self._datastore = open(self._datastore, encoding='utf8')
        if hasattr(self._datastore, 'readline'):
            line = self._datastore.readline()
            if line:
                return line
            else:
                raise EOFReached()
        elif hasattr(self._datastore, 'get'):
            try:
                val = self._datastore.get(block=False)
                return val
            except queue.Empty:
                return None
        return None

    def linesLeft(self):
        if hasattr(self._datastore, 'qsize'):
            return self._datastore.qsize()
        return -1

    def pushMessage(self, message):
        try:
            self._messages.put(message, block=False)
        except queue.Full:
            return False
        else:
            return True

    def popMessage(self):
        try:
            val = self._messages.get(block=False)
            return val
        except queue.Empty:
            return None

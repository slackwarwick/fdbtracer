import datetime
from enum import Enum


# Event Data
class EventData:
    _fields = list()

    @classmethod
    def setFields(cls, fields):
        cls._fields = fields

    def __init__(self):
        for field in self._fields:
            setattr(self, field, None)


# Event Data Parser
_DATEPART = slice(0, 10)
_TIMEPART = slice(11, 24)
_HHMMSS = slice(0, 8)
_MSEC = slice(-4, None)
_LINEBREAK = '\n'
_STATEMENTSTART = '-------------------------------------------------------------------------------'
_STATEMENTEND   = '^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^'
_TRANSACTIONPREFIX = '(TRA_'
_TCPV4PREFIX = 'TCPv4:'
_ATTPREFIX = '(ATT_'
_SQL_CLIENT_SIGNATURES = ('__SUPSQL__',)


class ParseState(Enum):
    SQLTEXT = 1
    OTHER = 2


class EventParser:
    def __init__(self):
        self._tmp = EventData()
        self._parsedEvent = None
        self._state = ParseState.OTHER

    def parse(self, line):
        line = line.rstrip('\n ')

        (new_date_time, new_event_name) = self._findEventInfo(line)
        if new_date_time:
            self._state = ParseState.OTHER
            if self._tmp.DATE_TIME:
                self._pushEvent()
            self._tmp = EventData()
            self._tmp.DATE_TIME = new_date_time
            self._tmp.EVENT_NAME = new_event_name
            self._tmp.RAW_OUTPUT = line
            return
        elif not self._tmp.RAW_OUTPUT:
            return
        else:
            self._tmp.RAW_OUTPUT = _LINEBREAK.join([self._tmp.RAW_OUTPUT, line])

        if self._isStatementStart(line):
            self._state = ParseState.SQLTEXT
            return

        if self._isStatementEnd(line):
            self._state = ParseState.OTHER
            return

        if self._state == ParseState.SQLTEXT:
            self._tmp.SQL_TEXT = line if not self._tmp.SQL_TEXT else _LINEBREAK.join([self._tmp.SQL_TEXT, line])
            return

        (transactionid, isolation_mode, rec_version, lock_mode, read_mode) = self._findTransactionInfo(line)
        if transactionid:
            self._tmp.TRANSACTIONID = transactionid
            self._tmp.ISOLATION_MODE = isolation_mode
            self._tmp.REC_VERSION = rec_version
            self._tmp.LOCK_MODE = lock_mode
            self._tmp.READ_MODE = read_mode
            return

        (attachmentid, user_name, remote_address) = self._findConnectionInfo(line)
        if attachmentid:
            self._tmp.ATTACHMENTID = attachmentid
            self._tmp.USER_NAME = user_name
            self._tmp.REMOTE_ADDRESS = remote_address
            return

        (module_name, module_line) = self._findModuleInfo(line)
        if module_name:
            self._tmp.MODULE_NAME = module_name
            self._tmp.MODULE_LINE = module_line
            return

        # etc...

    def popEvent(self):
        event = None
        if self._parsedEvent:
            event = self._parsedEvent
            self._parsedEvent = None
        return event

    def _pushEvent(self):
        self._parsedEvent = self._tmp

    def _findEventInfo(self, line):
        '''1234-12-12T12:12:12.1234 <...> EVENT_TYPE'''
        event_name = date_time = None
        if len(line) > 10 and line[4] == line[7] == '-' and line[10] == 'T':
            date = self._dateFromStr(line[_DATEPART])
            time = self._timeFromStr(line[_TIMEPART])
            if date and time:
                event_name = line.rstrip('\n').rpartition(' ')[2]
                date_time = datetime.datetime.combine(date, time)
        return (date_time, event_name)

    def _findModuleInfo(self, line):
        '''/*<SQL_CLIENT_SIGNATURE>/<MODULE_NAME>/<MODULE_LINE>*/'''
        module_name = module_line = None
        for signature in _SQL_CLIENT_SIGNATURES:
            idx = line.find(signature)
            if idx != -1:
                stripped = slice(idx, line.find('*/'))
                (_, module_name, module_line) = line[stripped].split('/')
                module_name = module_name.split('.')[0]
        return (module_name, module_line)

    def _findTransactionInfo(self, line):
        '''        (TRA_12345,  PAPAM1 | PARAM2 | PARAM3 |...)'''
        transactionid = isolation_mode = rec_version = lock_mode = read_mode = None
        line = line.strip()
        if line.startswith(_TRANSACTIONPREFIX):
            (transactionid, _, transactionParams) = line.lstrip(_TRANSACTIONPREFIX).rstrip(')').partition(',')
            transactionParams = tuple(a.strip() for a in transactionParams.split('|'))
            if (len(transactionParams) == 4):
                (isolation_mode, rec_version, lock_mode, read_mode) = transactionParams
            elif (len(transactionParams) == 3):
                (isolation_mode, lock_mode, read_mode) = transactionParams
        return (transactionid, isolation_mode, rec_version, lock_mode, read_mode)

    def _findConnectionInfo(self, line):
        '''       /path/to/database.fdb (ATT_123, LOGIN:NONE, ENCODING, TCPv4:123.123.123.123)'''
        attachmentid = user_name = remote_address = None
        ipIndex = line.find(_TCPV4PREFIX)
        if ipIndex != -1:
            remote_address = line[ipIndex+len(_TCPV4PREFIX):].rstrip(')')
            attIndex = line.find(_ATTPREFIX)
            if attIndex != -1:
                attSize = line[attIndex:].find(',')
                attachmentid = line[attIndex+len(_ATTPREFIX):attIndex+attSize]
                userIndex = attIndex+attSize+1
                userSize = line[userIndex:].find(':')
                user_name = line[userIndex:userIndex+userSize].strip()
        return (attachmentid, user_name, remote_address)

    def _isStatementStart(self, line):
        return _STATEMENTSTART in line

    def _isStatementEnd(self, line):
        return _STATEMENTEND in line

    def _dateFromStr(self, dateStr):
        try:
            lst = dateStr.split(sep='-', maxsplit=2)
            return datetime.date(year=int(lst[0]), month=int(lst[1]), day=int(lst[2]))
        except:
            return None

    def _timeFromStr(self, timeStr):
        try:
            msec = timeStr[_MSEC]
            lst = timeStr[_HHMMSS].split(sep=':', maxsplit=2)
            return datetime.time(hour=int(lst[0]), minute=int(lst[1]), second=int(lst[2]), microsecond=int(msec)*100)
        except:
            return None

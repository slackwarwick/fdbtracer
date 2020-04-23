import os
from pathlib import Path
import fdb

from appdata import Communicator, TracerMessage, TracerError, EOFReached
from eventdata import EventData, EventParser

_DB_NAME_PLACEHOLDER = '__DATABASENAME__'
_PARSEDFIELD_MARK = '/*__PARSEDFIELD__*/'
_dumpEngine = None


def run(dbPath, dbScriptPath, communicator):
    global _dumpEngine
    if not _dumpEngine:
        _dumpEngine = DumpEngine(dbPath, dbScriptPath, communicator)
    _dumpEngine.createDb()
    _dumpEngine.connect()
    _dumpEngine.runDump()


class DumpEngine:
    def __init__(self, dbPath, dbScriptPath, communicator):
        self._linesProcessed = 0
        self._eventsDumped = 0
        self._connection = None
        self._dbPath = dbPath
        self._dbScriptPath = dbScriptPath
        self._initEventDataFields()
        self._parser = EventParser()
        self._comm = Communicator(datastore=communicator._datastore, stop=communicator._stop, messages=communicator._messages) 

    def createDb(self):
        if os.path.exists(self._dbPath):
            self._comm.pushMessage(TracerMessage('Dump database file already exists.'))
            return
        try:
            self._createDb()
        except Exception as e:
            self._comm.pushMessage(TracerError(type(self), e))
        else:    
            self._comm.pushMessage(TracerMessage('Dump database file created: {}.'.format(self._dbPath)))

    def connect(self):
        if self._connected():
            self._comm.pushMessage(TracerError(type(self), 'Dump database is already connected.'))
        try:
            self._connect()
        except Exception as e:
            self._comm.pushMessage(TracerError(type(self), e))
        self._comm.pushMessage(TracerMessage('Connected to dump database.'))

    def runDump(self):
        while True:
            try:
                line = self._comm.popLine()
                if line:
                    self._parser.parse(line)
                    self._linesProcessed += 1
                    event = self._parser.popEvent()
                    if event:
                        self._dump(event)
                        self._eventsDumped += 1
                        if self._eventsDumped % 10000 == 0:
                            self._comm.pushMessage(TracerMessage('Dumped {} events, {} lines processed, {} lines left.'.format(
                                self._eventsDumped, self._linesProcessed, self._comm.linesLeft())
                                )
                            )
            except EOFReached:
                print('\nAll data has been processed. Exiting...')
                self._comm.stop()
                break
            except Exception as e:
                self._comm.pushMessage(TracerError(type(self), e))        
            if self._comm.stopped():
                break
        self.disconnect()

    def _dump(self, event):
        try:
            self._connection.begin()
            cur = self._connection.cursor()
            fields = vars(event)
            fieldNames = ','.join(tuple(fields.keys()))
            fieldValues = tuple(fields.values())
            placeholders = ','.join('?'*len(fields))
            cur.execute('insert into trace_data_parsed ({}) values ({}) '.format(fieldNames, placeholders), fieldValues)
        except Exception as e:
            self._connection.rollback()
            self._comm.pushMessage(TracerError(type(self), e))
        self._connection.commit()

    def disconnect(self):
        if not self._connected():
            self._comm.pushMessage(TracerError(type(self), 'Database is already disconnected.'))        
        try:
            self._disconnect()
        except Exception as e:
            self._comm.pushMessage(TracerError(type(self), e))
        else:
            self._comm.pushMessage(TracerMessage('Disconnected from Dump database.'))

    def _createDb(self):
        scriptFile = Path(self._dbScriptPath)
        script = ''
        with scriptFile.open() as f:
            script = f.read()
        script = script.replace(_DB_NAME_PLACEHOLDER, self._dbPath).split('@')
        for operation in script:
            if 'CREATE DATABASE' in operation.upper():
                fdb.create_database(sql=operation)
            else:
                if not self._connected():
                    self._connect()
                self._connection.cursor().execute(operation)
        if self._connected():
            if self._connection.main_transaction.active:
                self._connection.commit()
            self._disconnect()

    def _initEventDataFields(self):
        scriptFile = Path(self._dbScriptPath)
        fieldNames = list()
        with scriptFile.open() as f:
            fieldNames = [line.split(maxsplit=1)[0] for line in f if _PARSEDFIELD_MARK in line]
            EventData.setFields(fieldNames)

    def _connect(self):
        self._connection = fdb.connect(database=self._dbPath, user='SYSDBA', password='masterke', charset='WIN1251')

    def _disconnect(self):
        self._connection.close()

    def _connected(self):
        return self._connection and not self._connection.closed

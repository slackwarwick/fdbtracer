import fdb
import appdata
from appdata import Communicator, TracerMessage, TracerError

_traceEngine = None


def run(params, communicator):
    global _traceEngine
    if not _traceEngine:
        _traceEngine = TraceEngine(params, communicator)
    _traceEngine.connect()
    _traceEngine.runTrace()


class TraceEngine:
    def __init__(self, params, communicator):
        self._traceParams = None
        self._svc = None
        self._svcAux = None
        self._traceId = 0
        self._traceParams = appdata._TraceParameters(params.host, params.login, params.password, params.traceConf)
        self._comm = Communicator(datastore=communicator._datastore, stop=communicator._stop, messages=communicator._messages)

    def connect(self):
        try:
            self._svc = fdb.services.connect(host=self._traceParams.host, user=self._traceParams.login, password=self._traceParams.password)
            if self._svc.engine_version >= 3.0:
                self._svc.charset = 'UTF8'
            # Because trace session blocks the connection, we need another one to stop trace session!
            self._svcAux = fdb.services.connect(host=self._traceParams.host, user=self._traceParams.login, password=self._traceParams.password)
            self._traceId = self._svc.trace_start(self._traceParams.traceConf, 'test_trace1')
        except Exception as e:
            self._comm.pushMessage(TracerError(type(self), e))
        else:
            self._comm.pushMessage(TracerMessage("Connected to traced DB."))

    def disconnect(self):    
        try:
            self._svcAux.trace_stop(self._traceId)
            self._svcAux.close()
            self._svc.close()
            self._traceId = 0
        except Exception as e:
            self._comm.pushMessage(TracerError(type(self), e))
        else:    
            self._comm.pushMessage(TracerMessage("Disconnected from traced DB."))

    def connected(self):
        return self._traceId != 0

    def runTrace(self):
        while True:
            try:
                line = self._svc.readline()
                while not self._comm.pushLine(line):
                    if self._comm.stopped():
                        break
            except Exception as e:
                self._comm.pushMessage(TracerError(type(self), e))
            if self._comm.stopped():
                break
        self.disconnect()

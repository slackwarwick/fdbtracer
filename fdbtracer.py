# python3
import os
import argparse
import configparser
import threading
from multiprocessing import Process
import traceengine
import dumpengine
import logger
import appdata
from appdata import Communicator


class Signal:
    stop = False


class FDBTracer:
    def __init__(self, signal, filename=None):
        self._errorsCount = 0
        self._signal = signal
        self._filename = filename
        self._comm = Communicator(datastore=filename) if filename else Communicator()
        try:
            self.LoadParametersFromConfFile()
        except Exception as e:
            print("Load parameters from config file error: {}".format(str(e)))
            print("Terminating.")
            exit()
        try:
            self._logger = logger.Logger(appdata.common().logPath, 
                appdata.common().logLevel if not appdata.common().testMode else logger.DEBUG,
                appdata.common().consoleDebug)
        except Exception as e:
            print("Can not initialize Logger Class: {}".format(str(e)))
        except:
            print('Can not open log file on path: {}'.format(appdata.common().logPath))
            print("Terminating.")
            exit()

    def run(self):
        dataProvider = None
        dumpHandler = None
        if self._filename:
            self._logger.debug('Trying to open file {}...'.format(self._filename))
        else:
            self._logger.debug('Trying to start trace...')
            dataProvider = Process(target=traceengine.run, args=(appdata.trace(), self._comm,))
        dumpHandler = Process(target=dumpengine.run, args=(appdata.absDumpDbPath(), appdata.absDumpDbScriptPath(), self._comm,))
        if dataProvider:
            dataProvider.start()
        dumpHandler.start()
        self.runMessagesHandling()
        self._comm.stop()
        if dataProvider:
            dataProvider.join()
        dumpHandler.join()
        self._logger.debug('All tasks done, finishing!')

    def LoadParametersFromConfFile(self):
        config = configparser.ConfigParser()
        config.read('{}/{}.conf'.format(os.getcwd(), appdata.PROGRAM_NAME), encoding='utf8')
        SYS_SECTION = "system"
        appdata.initCommonParams(
            testMode=       config.getboolean(SYS_SECTION, "testMode", fallback=False),
            logPath=        config.get(SYS_SECTION, "logPath", fallback=''),
            logLevel=       config.getint(SYS_SECTION, "logLevel", fallback=1),
            consoleDebug=   config.getboolean(SYS_SECTION, "consoleDebug", fallback=False),
            maxErrors=      config.getint(SYS_SECTION, "maxErrors", fallback=50)
        )
        TRACE_SECTION = "traced_db"
        appdata.initTraceParams(
            host=       config.get(TRACE_SECTION, "host", fallback=''),
            login=      config.get(TRACE_SECTION, "login", fallback=''),
            password=   config.get(TRACE_SECTION, "password", fallback=''),
            traceConf=  config.get(TRACE_SECTION, "traceConf", fallback='')
        )
        DUMP_SECTION = "dump_db"
        appdata.initDumpParams(
            databasePath=   config.get(DUMP_SECTION, "databasePath", fallback=''),
            databaseName=   config.get(DUMP_SECTION, "databaseName", fallback=''),
            addDateToName=  config.getboolean(DUMP_SECTION, "addDateToName", fallback=False)
        )

    def saveParametersToLogFile(self):
        self._logger.debug("FDBTracer started...")
        self._logger.debug("System Parameters Listing:")
        self._logger.debug("Test mode: {}".format(appdata.common().testMode))
        self._logger.debug("Log Path: {}".format(appdata.common().logPath))
        self._logger.debug("Log Level: {}".format(appdata.common().logLevel))
        self._logger.debug("Console Debug: {}".format(appdata.common().consoleDebug))

        self._logger.debug("Traced Database Parameters Listing:")
        self._logger.debug("DB Host: {}".format(appdata.trace().host))
        self._logger.debug("DB Login: {}".format(appdata.trace().login))

        self._logger.debug("Dump Database Parameters Listing:")
        self._logger.debug("DB Path: {}".format(appdata.absDumpDbPath()))

    def runMessagesHandling(self):
        while True:
            message = self._comm.popMessage()
            if message:
                if message.iserror:
                    self._logger.critical('Got error from {}, text: {}'.format(message.source, message.text))
                    self._errorsCount += 1
                    if self._errorsCount > appdata.common().maxErrors:
                        self._logger.critical('Maximum errors reached, stopping.')
                        print('\nMaximum errors reached. see log for details. Exiting...')
                        break
                else:       
                    self._logger.debug(message.text)
                    self._errorsCount = 0
            if self._signal.stop or self._comm.stopped():
                break


def waitForInterrupt(signal, msg):
    while True:
        if input(msg) == 'q':
            signal.stop = True
            break


if __name__ == '__main__':
    argsp = argparse.ArgumentParser()
    argsp.add_argument('-f', '--file', help='If specified, parse FB Trace and Audit log file with given name and exit')
    argsp.add_argument('-d', '--database', help='If specified, use DB file with given name for parsed data')
    args = argsp.parse_args()

    if args.database:
        appdata.overrideDumpDbPath(args.database)

    signal = Signal()

    if args.file:
        if not os.path.exists(args.file):
            print('File {} does not exist! Exiting.'.format(args.file))
            exit()
        msg = 'Parsing file {}. Type \'q\' to quit or wait for finish: '.format(args.file)
        tracer = FDBTracer(signal, args.file)
    else:
        msg = 'Trace started. Type \'q\' to quit: '
        tracer = FDBTracer(signal)

    interruptHook = threading.Thread(target=waitForInterrupt, args=(signal, msg,), daemon=True)
    interruptHook.start()
    tracer.run()
    print('Bye!')

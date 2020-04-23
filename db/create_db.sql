/*
    Script for Dump Database creation. Firebird 2.5 or 3.0 Embedded Server should be available in PATH or placed to application dir.
    
    * '__DATABASENAME__' is a placeholder for absolute DB path, filled automatically from program .conf file. Not for manual modification!
    * Operations are delimited with 'At' symbol, used by Python str.split() mechanism.
    * Mark fields that should be parsed with '__PARSEDFIELD__' comment, and then add them to parse() method of event parser class.
*/

CREATE DATABASE '__DATABASENAME__'
USER 'SYSDBA' PASSWORD 'masterke'
PAGE_SIZE 4096
DEFAULT CHARACTER SET WIN1251 COLLATION WIN1251

@
CREATE TABLE TRACE_DATA_PARSED (
    ID              INTEGER NOT NULL,
    CREATED         TIMESTAMP DEFAULT current_timestamp,
    DATE_TIME       TIMESTAMP,                              /*__PARSEDFIELD__*/
    EVENT_NAME      VARCHAR(31),                            /*__PARSEDFIELD__*/
    TRANSACTIONID   INTEGER,                                /*__PARSEDFIELD__*/
    ISOLATION_MODE  VARCHAR(15),                            /*__PARSEDFIELD__*/
    REC_VERSION     VARCHAR(15),                            /*__PARSEDFIELD__*/
    LOCK_MODE       VARCHAR(15),                            /*__PARSEDFIELD__*/
    READ_MODE       VARCHAR(15),                            /*__PARSEDFIELD__*/
    ATTACHMENTID    BIGINT,                                 /*__PARSEDFIELD__*/
    USER_NAME       VARCHAR(128),                           /*__PARSEDFIELD__*/
    REMOTE_ADDRESS  VARCHAR(255),                           /*__PARSEDFIELD__*/
    MODULE_NAME     VARCHAR(120),                           /*__PARSEDFIELD__*/
    MODULE_LINE     INTEGER,                                /*__PARSEDFIELD__*/
    SQL_TEXT        BLOB SUB_TYPE 1 SEGMENT SIZE 80,        /*__PARSEDFIELD__*/
    RAW_OUTPUT      BLOB SUB_TYPE 1 SEGMENT SIZE 80         /*__PARSEDFIELD__*/
)

@
CREATE SEQUENCE GEN_TRACE_DATA_PARSED

@
CREATE OR ALTER TRIGGER TRACE_DATA_PARSED_BI FOR TRACE_DATA_PARSED
ACTIVE BEFORE INSERT POSITION 0
AS
BEGIN
  IF (NEW.ID IS NULL) THEN
    NEW.ID = GEN_ID(GEN_TRACE_DATA_PARSED,1);
END

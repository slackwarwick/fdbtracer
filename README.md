# fdbtracer

**fdbtracer** is Firebird Trace tool that uses Firebird Trace API and parses its plain text output to the set of database table fields.

It can be used in two ways:
* to connect to your Firebird Database and parse the output of the trace session (user trace mode).
* to parse the contents of given trace log file (system trace mode).

**fdbtracer** uses its own Embedded Firebird Database to dump the results of the trace. 

Should work with Firebird 2.5 and Firebird 3.0 Databases.

## List of files and dirs:

*fdbtracer.conf* - main config file.
*db* - dir containing *create_db.sql* script and the default path for the Firebird Embedded Databases.
*db/create_db.sql* - file with SQL commands for creating the Embedded Firebird Database.
*fdbtracer.py* - main script.
*trace3.conf*, *trace2.conf* etc. - Trace API config files. Used syntax depends on the version of Firebird Server (2.5 or 3.0).
**.py* - other python modules.

## Usage:

`#python fdbtracer.py` - start user trace session (connects to trace database specified in the main and trace config files).

`#python fdbtracer.py --database <path>` - start user trace session and override the dump database path.

`#python fdbtracer.py --file <filename>` - start parsing the log file with given filename.


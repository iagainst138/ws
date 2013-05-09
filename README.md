ws
==

A python script to share a directory through HTTP.

By default it shares the current working directory.

Options:
    -d <path to directory>
        - directory to share
    -u <user>
        - user for basic HTTP authentication
        - if -p is not specified user is prompted for a password
    -p <password>
        - password to use for basic HTTP authentication
    -P <port>
        - port to share on

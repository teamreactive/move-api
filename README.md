# move-api

[![No Maintenance Intended](http://unmaintained.tech/badge.svg)](http://unmaintained.tech/)

:motor_scooter: The back-end of Move, a service that shows you the nearest places selling what you need and delivers your order wherever you are. A REST API written in Flask.

## Usage
You need [PostgreSQL](https://www.postgresql.org/) and [virtualenv](https://virtualenv.pypa.io/) installed on your machine.

Create a database and a user for it:
```
initdb /usr/local/var/postgres
createuser -P -s -e <user>
createdb mydb
```

Create a virtual environment and install the dependencies:
```
virtualenv flask
flask/bin/pip install -r requirements.txt
```

Put the database credentials in a `.env` file in the root folder, then start the database and the API:
```
postgres -D /usr/local/var/postgres
./app.py
```

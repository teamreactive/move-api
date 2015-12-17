# Move API

Move API is the server-side of Move app, a simple REST API written in Flask.

### Version
1.0.0

### Installation

You need to install **postgresql** database:
```sh
$ brew install postgresql
```

Initialize the just installed database:
```sh
$ initdb /usr/local/var/postgres
```

Create a new user for the database system with the given credentials:
```sh
$ createuser -P -s -e <user>
```

Create a new database called *mydb*:
```sh
$ createdb mydb
```

You need to have **virtualenv** installed globally in your machine:
```sh
$ [sudo] pip install virtualenv
```

Inside the root folder, create a new virtual environment called *flask*:
```sh
$ virtualenv flask
```

Install all the dependencies included in the file *requirements.txt*:
```sh
$ flask/bin/pip install requirements.txt
```

Give execution permissions to the **app.py** script:
```sh
$ chmod a+x app.py
```

Inside the root folder, make a new file called *.env* that contains all credentials:
```sh
$ touch .env
```

### Running

Run the postgres server:
```sh
$ postgres -D /usr/local/var/postgres
```

Run the **app.py** script:
```sh
$ ./app.py
```

### Development

Every time you install new dependencies, overwrite the *requirements.txt* file:
```sh
$ flask/bin/pip freeze > requirements.txt
```

License
----

No License
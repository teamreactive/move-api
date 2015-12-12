# Move API

Move API is the server-side of Move app, a simple REST API written in Flask.

### Version
1.0.0

### Installation

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
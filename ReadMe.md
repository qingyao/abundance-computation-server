# A minimal Flask web server to compute abundance from sequence count/intensity file

## install in local environment
```
pip install -r requirements.txt
```

## set up environment variables
* SECRET_KEY
* PORT

## To serve
```
gunicorn -w {number of workers} wsgi:app
```


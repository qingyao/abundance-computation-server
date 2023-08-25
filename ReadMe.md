# A minimal Flask web server to compute abundance from sequence count/intensity file

## install in local environment
```
pip install -r requirements.txt
```

## set up environment variables
* SECRET_KEY
* PORT
* SSE_PORT
* WORKERS
* ACCESSLOG
* ERRORLOG

## To serve
```
gunicorn wsgi:app
gunicorn sse:app -c gunicorn.conf.sse.py
```


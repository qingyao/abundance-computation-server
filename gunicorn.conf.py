from dotenv import load_dotenv
import os

load_dotenv()
bind = "127.0.0.1:" + os.getenv('PORT')
workers = os.getenv('WORKERS')
accesslog = os.getenv('ACCESSLOG')
errorlog = os.getenv('ERRORLOG')
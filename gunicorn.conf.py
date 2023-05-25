from dotenv import load_dotenv
import os

load_dotenv()
bind = os.getenv('BIND')
workers = os.getenv('WORKERS')
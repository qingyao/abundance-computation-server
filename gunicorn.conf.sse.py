from dotenv import load_dotenv
import os

load_dotenv()
bind = "127.0.0.1:" + os.getenv('SSE_PORT')
accesslog = os.getenv('ACCESSLOG')
errorlog = os.getenv('ERRORLOG')
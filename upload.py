import requests
import sys

url = "http://192.168.1.66:5000/upload"
files = {'file': (sys.argv[1],open(sys.argv[1], 'rb'))}
r = requests.post(url, files=files)

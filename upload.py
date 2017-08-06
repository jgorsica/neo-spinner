import requests
import sys

url = "http://192.168.1.66:5000/upload"
files = {'files': open(sys.argv[1], 'rb')}
r = requests.post(url, files=files)

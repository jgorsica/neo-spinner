import requests
import sys

url = "http://192.168.1.66:5000/upload"
args = {'file': open(sys.argv[1], 'rb'), 'filename':sys.argv[1]}
r = requests.post(url, args=args)

from flask import Flask
from flask import request
import time
import neorotate

app = Flask(__name__)

@app.route('/')
def hello_world():
	return 'Hello World!'

@app.route('/upload', methods = ['GET', 'POST'])
def upload_file():
	if request.method == 'POST':
		f = request.files['files']
    		filename='pic.png'
		f.save(filename)
		show_it(filename)
		return '200'
	else:
		return 'Upload Page'

def show_it(filename):
	exec(open("./neorotate.py").read(),filename)

if __name__ == '__main__':
	app.debug = False
	app.run(host='0.0.0.0')
  

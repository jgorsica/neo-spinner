from flask import Flask
from flask import request
import time
import PIL
from PIL import Image
import numpy as np
from neopixel import *
from neodisplay import *

app = Flask(__name__)
# LED strip configuration:
LED_COUNT      = 60      # Number of LED pixels.
LED_PIN        = 21      # GPIO pin connected to the pixels (18 uses PWM!).
#LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 5       # DMA channel to use for generating signal (try 5)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
LED_STRIP      = ws.WS2811_STRIP_GRB   # Strip type and colour ordering
# Display Configuration
MIRRORED=True
STAGGERED=True
WIDTH=8
HEIGHT=8
PAIR=2*WIDTH-1 if STAGGERED else 2*WIDTH

@app.route('/')
def hello_world():
	return 'Hello World!'

@app.route('/upload', methods = ['GET', 'POST'])
def upload_file():
	if request.method == 'POST':
		f = request.files['files']
		f.save('pic.png')
		show_it()
		return '200'
	else:
		return 'Upload Page'

def show_it():
	# Create NeoPixel object with appropriate configuration.
	strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP)
	# Intialize the library (must be called once before other functions).
	strip.begin()
	disp=NeoDisplay(WIDTH,HEIGHT,STAGGERED,MIRRORED)
	print ('Press Ctrl-C to quit.')
	pcl=disp.getPixelColorList('pic.png')
	print(pcl)
	print ('Showing Image.')
	disp.showImage([strip],pcl)

if __name__ == '__main__':
	app.debug = False
	app.run(host='0.0.0.0')
	

	

		
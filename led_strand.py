import sys
sys.path.append('/home/pi/rpi_ws281x/python') # check path to neopixel library location
from neopixel import *

class LED_strand(object):
     
     LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
     LED_BRIGHTNESS = 16     # Set to 0 for darkest and 255 for brightest
     LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
     LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
     LED_STRIP      = ws.WS2811_STRIP_GRB   # Strip type and colour ordering
     
     def __init__(self, led_count=10, pin=21, dma_channel=5, theta=0, radius_list=None, freq=LED_FREQ_HZ, \
                 invert=LED_INVERT, brightness=LED_BRIGHTNESS, channel=LED_CHANNEL, strip_type=LED_STRIP):
          self.led_count=led_count
          self.radius_list=radius_list
          self.theta=theta
          self.brightness=brightness
          self.pin=pin
          self.strand = Adafruit_NeoPixel(self.led_count, pin, freq, dma_channel, invert, self.brightness, channel, strip_type)
          
     def begin(self):
          self.strand.begin()
          
     def setPixelColor(self, index, color):
          self.strand.setPixelColor(index, color)
          
     def show(self):
          self.strand.show()
          
     def get_count(self):
          return self.led_count
     
     def get_theta(self):
          return self.theta
     
     def get_radius_list(self):
          return self.radius_list
     
     def get_radius(self, index):
          return self.radius_list[index]

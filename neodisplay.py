import PIL
from PIL import Image
import numpy as np
from neopixel import *

class NeoDisplay(object):
	def __init__(self,width,height,staggered,mirrored):
		self.width = width
		self.height = height
		self.staggered = staggered
		self.mirrored = mirrored
		self.pair = 2*width-1 if staggered else 2*width

	def getPixelColorList(self, image_file):
		im = Image.open(image_file).convert('RGBA')
		background = Image.new('RGBA',im.size,(0,0,0))
		alpha_composite = Image.alpha_composite(background,im)
		alpha_composite.thumbnail([self.height,self.width],Image.ANTIALIAS)
		alpha_composite.save('thumb.png')
		arr=np.array(alpha_composite)
		return arr

	def showImage(self, strip_list, pcl):
		row_offset=0
		for strip in strip_list:
			for pixel in range(0,strip.numPixels()):
				row = pixel//self.pair*2 + (pixel%self.pair)//self.width + row_offset
				first=((row%2)==1)
				col = self.width-1-pixel%self.pair%self.width if ((self.staggered and first) ^ self.mirrored) else pixel%self.pair%self.width
				color=pcl[row][col]/2+pcl[row][col+(1 if self.mirrored else -1)]/2 if (self.staggered & first) else pcl[row][col]
				color=color/16
				strip.setPixelColor(pixel, Color(color[0],color[1],color[2]))
				last_row=row
			row_offset=last_row + 1
			strip.show()
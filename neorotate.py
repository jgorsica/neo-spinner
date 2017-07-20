import math
import time
import numpy as np
import PIL
from PIL import Image
from multiprocessing import Process
from led_strand import LED_strand
from icm_20601 import ICM_20601

# LED strip configuration:
LED_COUNT_1      = 144      # Number of LED pixels.
LED_PIN_1        = 10      # GPIO pin connected to the pixels (18 uses PWM!).
LED_DMA_1        = 5       # DMA channel to use for generating signal (try 5)
LED_ANGLE_1 = 0

LED_COUNT_2      = 144      # Number of LED pixels.
LED_PIN_2        = 21      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_DMA_2       = 6       # DMA channel to use for generating signal (try 5)
LED_ANGLE_2 = 90

I2C_BUS = 1
SENSOR_ADDRESS = 0x69

TRIM_A=0 #speed dependent angular offset
TRIM_B=0 #speed independent angualr offset
NOISE_THRESHOLD=0.05 #accel count delta to trigger direction change

def Color(red, green, blue, white = 0):
	"""Convert the provided red, green, blue color to a 24-bit color value.
	Each color component should be a value 0-255 where 0 is the lowest intensity
	and 255 is the highest intensity.
	"""
	return (white << 24) | (red << 16)| (green << 8) | blue

#takes image file and produces array of RGBA pixel values for black padded, alpha blended image of correct size
def getImageArray(image_file, width, height):
	im = Image.open(image_file).convert('RGBA')
	im.thumbnail([height,width],Image.ANTIALIAS)
	im_width, im_height = im.size
	padded_thumb = Image.new('RGBA',(width, height), (0, 0, 0))
	paste_x_offset = (width-(im_width))//2
	paste_y_offset = (height-(im_height))//2
	paste_region = (paste_x_offset,paste_y_offset,paste_x_offset+im_width-1, \
			paste_y_offset+im_height-1)
	#print (im.size)
	#print (paste_region)
	#print (padded_thumb.size)
	padded_thumb.paste(im, (paste_x_offset,paste_y_offset))
	background = Image.new('RGBA',[height,width],(0,0,0))
	alpha_composite = Image.alpha_composite(background,padded_thumb)
	alpha_composite.save('thumb.png')
	arr=np.array(alpha_composite)
	return arr

#takes image pixel array and parameters describing physical LED strip configuration, 
#produces a precalculated array for each strip at each angle
def get_angular_image(image_array,angle_list,led_strips):
  longest_strip_length = 0
  for strip in led_strips:
    if strip.get_count()>longest_strip_length:
      longest_strip_length = strip.get_count()
  angular_image=np.zeros((len(led_strips),len(angle_list),longest_strip_length), dtype=np.int)
  radius = 0
  for strip in led_strips:
    candidate = max([abs(x) for x in strip.get_radius_list()])
    if candidate > radius:
      radius = candidate
  for strip_index in xrange(len(led_strips)):
    for theta in angle_list:
      cos_t = math.cos(theta*math.pi/180.+led_strips[strip_index].get_theta())
      sin_t = math.sin(theta*math.pi/180.+led_strips[strip_index].get_theta())
      for led_index in xrange(led_strips[strip_index].get_count()):
        led_radius = led_strips[strip_index].get_radius_list()[led_index]
        x_r = led_radius * sin_t
        y_r = led_radius * cos_t
        #change is image coordinate system
        x = x_r + radius
        y = radius - y_r
        x1 = int(x)
        x2 = x1+1
        if x2 == image_array.shape[0]:
          x2 = x1
        y2 = int(y)
        y1 = y2+1
        if y1 == image_array.shape[1]:
          y1 = y2
        #get four closest pixels and bilaterally interpolate
        p11=image_array[x1,y1]
        p21=image_array[x2,y1]
        p12=image_array[x1,y2]
        p22=image_array[x2,y2]
        p=(y-y2)*(x-x1)*p21+(x2-x)*(y-y2)*p11+(y1-y)*(x-x1)*p22+(x2-x)*(y1-y)*p12
        alpha=p[3]/255.
        color=Color(int(p[0]*alpha),int(p[1]*alpha),int(p[2]*alpha))
        angular_image[strip_index,theta,led_index]=color
  return angular_image
  
def get_sensor_data(sensor):
  ts, accel, gyro, _ = sensor.get_sensor_data()
  return [ts,accel[1],gyro[2]]
  
'''uses sensor data to determine exact angular position of the spinner'''
prev_theta = 0 #angle of rotation, 0 = up
y_dir = 0 #trend of accel_y data
y_prev_dir=0 #previous_trend of accel_y data
y_prev=0 #previous accel_y_data
prev_ts=0 #previous timestamp
def get_theta(sensor_data):
  global prev_theta, y_dir, y_prev_dir, y_prev, prev_ts
  v=sensor_data[2] # rotational velocity dps
  y=sensor_data[1] # accel_y in integer counts
  ts=sensor_data[0]
  if (ts-prev_ts) > 5:
    prev_ts = ts
    y_prev = y
    y_prev_dir = 0
    y_dir = 0
  theta = prev_theta + v*(ts-prev_ts)
  while theta>=360:
    theta -= 360
  if (y-y_prev)>NOISE_THRESHOLD:
    y_dir=1
    y_prev=y
  elif (y_prev-y)>NOISE_THRESHOLD:
    y_dir=-1
    y_prev=y
  if (y_dir==-1 and y_prev_dir==1):
    offset=TRIM_A*v+TRIM_B
    theta=(theta+offset)//2
  prev_ts=ts
  y_prev_dir=y_dir
  prev_theta = theta
  return theta
  
#returns lists for pixel colors for each LED in each strip based on the angular position of the LED
#at the time it receives its color command
def get_pixel_colors(angular_image, theta, sensor_data):
  angular_pixel_delay = 0.00003 * sensor_data[2]
  pixel_colors=np.zeros((angular_image.shape[0],angular_image.shape[2]),dtype=np.int)
  for strip_index in xrange(angular_image.shape[0]):
    for led_index in xrange(angular_image.shape[2]):
      pixel_theta = int(theta + led_index * angular_pixel_delay)
      while pixel_theta >= 360:
        pixel_theta -= 360
      pixel_color = angular_image[strip_index,pixel_theta,led_index]
      pixel_colors[strip_index,led_index]=pixel_color
  return pixel_colors

def turn_off_leds(led_strips):
  for strip in led_strips:
	for led_index in xrange(strip.get_count()):
		strip.setPixelColor(led_index, 0)
	strip.show()
	time.sleep(2)
	
def update_strip(strip, pixel_colors_for_strip):
  for led_index in xrange(strip.get_count()):
	strip.setPixelColor(led_index, pixel_colors_for_strip[led_index])
  strip.show()
	
def update_loop(strip, pixel_colors_by_angle):
  global theta
  update_count = 0
  while True:
    if theta >= 0: #spinning fast enough
      print(theta)
      #pixel_colors = get_pixel_colors(angular_image, theta, sensor_data)
      #pixel_colors = angular_image[:,theta,:]
      update_strip(strip, pixel_colors_by_angle[theta])
      update_count += 1
      if update_count%20 == 0:
        print(str(update_count) +' updates')
    else:
	turn_off_leds([strip])
    
  
if __name__ == '__main__':
  global theta
  sensor = ICM_20601(I2C_BUS, SENSOR_ADDRESS)
  radius_list_1=np.linspace((LED_COUNT_1-1)/2.,-1*((LED_COUNT_1-1)/2.),LED_COUNT_1).tolist()
  strip1 = LED_strand(LED_COUNT_1, LED_PIN_1, LED_DMA_1, LED_ANGLE_1, radius_list_1)
  radius_list_2=np.linspace((LED_COUNT_2/2.),1,LED_COUNT_2/2).tolist() + np.linspace(-1,-1*(LED_COUNT_2/2.),LED_COUNT_2/2).tolist()
  strip2 = LED_strand(LED_COUNT_2, LED_PIN_2, LED_DMA_2, LED_ANGLE_2, radius_list_2)
  strip1.begin()
  strip2.begin()
  print('strands initialized')
  led_strips = [strip1,strip2]
  angle_list = xrange(0,360,1)
  strip_led_count_list=[LED_COUNT_1,LED_COUNT_2]
  print('getting image array...')
  image_array = getImageArray('colors.png', LED_COUNT_1, LED_COUNT_1)
  print('getting angular image...')
  angular_image = get_angular_image(image_array,angle_list,led_strips)
  print ('Press Ctrl-C to quit.')
  processes=[]
  for strip_index in xrange(len(led_strips)):
    new_process=Process(target=update_loop,args=(led_strips[strip_index],angular_image[strip_index,:,:],))
    processes.append(new_process)
    new_process.start()
  while True:
    sensor_data = get_sensor_data(sensor)
    sensor_data[2]=100
    if sensor_data[2]>90: #spinning fast enough
      theta = get_theta(sensor_data)
      print(theta)
    else:
      theta = -1
    time.sleep(0.001)
  for process in processes:
      process.join()

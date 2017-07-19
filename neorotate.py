import math
import numpy as np
import PIL
from PIL import Image
from multiprocessing import Process
from led_strand import LED_strand

# LED strip configuration:
LED_COUNT_1      = 144      # Number of LED pixels.
LED_PIN_1        = 10      # GPIO pin connected to the pixels (18 uses PWM!).
LED_DMA_1        = 5       # DMA channel to use for generating signal (try 5)
LED_ANGLE_1 = 0

LED_COUNT_2      = 144      # Number of LED pixels.
LED_PIN_2        = 21      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_DMA_2       = 6       # DMA channel to use for generating signal (try 5)
LED_ANGLE_2 = 90

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
	print (im.size)
	print (paste_region)
	print (padded_thumb.size)
	padded_thumb.paste(im, (paste_x_offset,paste_y_offset))
	background = Image.new('RGBA',[height,width],(0,0,0))
	alpha_composite = Image.alpha_composite(background,padded_thumb)
	alpha_composite.save('thumb.png')
	arr=np.array(alpha_composite)
	return arr

#takes image pixel array and parameters describing physical LED strip configuration, 
#produces a precalculated array for each strip at each angle
def get_angular_image(image_array,angle_list,led_strips):
  angular_image=[]
  for strip in led_strips:
    strip_list=[]
    for theta in angle_list:
      cos_t = math.cos(theta*math.pi/180.+strip.get_theta())
      sin_t = math.sin(theta*math.pi/180.+strip.get_theta())
      pixel_list=[]
      for led_index in xrange(strip.get_count()):
        led_radius = strip.get_radius_list()[led_index]
        x_r = led_radius * sin_t
        y_r = led_radius * cos_t
        #change is image coordinate system
        x = x_r + radius
        y = radius - y_r
        x1 = floor(x)
        x2 = x1+1
        y2 = floor(y)
        y1 = y2+1
        #get four closest pixels and bilaterally interpolate
        p11=image_array[x1][y1]
        p21=image_array[x2][y1]
        p12=image_array[x1][y2]
        p22=image_array[x2][y2]
        p=(y-y2)*(x-x1)*p21+(x2-x)*(y-y2)*p11+(y1-y)*(x-x1)*p22+(x2-x)*(y1-y)*p12
        alpha=p[3]/255.
        pixel_list.append([p[0]*alpha,p[1]*alpha,p[2]*alpha])
      strip_list.append(strip_list)
    angular_image.append(angle_list)
  return angular_image
  
def get_sensor_data():
  ts=0
  accel_y=0
  gyro_z=0
  return [ts,accel_y,gyro_z]
  
'''uses sensor data to determine exact angular position of the spinner'''
a=0 #speed dependent angular offset
b=0 #speed independent angualr offset
noise_threshold=10 #accel count delta to trigger direction change
theta = b #angle of rotation, 0 = up
y_dir = 0 #trend of accel_y data
y_prev_dir=0 #previous_trend of accel_y data
y=0 #current accel_y data
y_prev=0 #previous accel_y_data
ts=0 #current timestamp
prev_ts=0 #previous timestamp
def get_theta(sensor_data):
  v=sensor_data[2] # rotational velocity dps
  y=sensor_data[1] # accel_y in integer counts
  ts=sensor_data[0]
  theta += v*(ts-prev_ts)
  if (y-y_prev)>noise_threshold:
    y_dir=1
    y_prev=y
  elif (y-y_prev)<noise_threshold:
    y_dir=-1
    y_prev=y
  if (y_dir==-1 and y_dir_prev==1):
    offset=a*v+b
    theta=(theta+offset)//2
  prev_ts=ts
  y_prev_dir=y_dir
  return theta
  
#returns lists for pixel colors for each LED in each strip based on the angular position of the LED
#at the time it receives its color command
def get_pixel_colors(angular_image, theta, sensor_data):
  angular_pixel_delay = 0.00003 * sensor_data[2]
  pixel_colors=[]
  for strip_index in xrange(len(angular_image)):
    single_strip=[]
    for led_index in xrange(len(angular_image[strip_index][0])):
      pixel_theta = math.floor(theta + pixel_index * angular_pixel_delay)
      pixel_color = angular_image[strip_index][pixel_theta][led_index]
      single_strip.append(pixel_color)
    pixel_colors.append(single_strip)
  return pixel_colors

def turn_off_leds(led_strips):
  for strip_index in xrange(len(led_strips)):
	for led_index in xrange(strip_led_count_list[strip_index].get_count()):
		led_strips[strip_index].setPixelColor(led_index, Color(0,0,0))
	led_strips[strip_index].show()
	
def update_strip(strip, pixel_colors):
  for led_index in xrange(strip.get_count()):
	color=pixel_colors[led_index]
	strip.setPixelColor(led_index, Color(color[0],color[1],color[2]))
  strip.show()
  
if __name__ == '__main__':
  radius_list_1=np.linspace((LED_COUNT_1-1)/2.,-1*((LED_COUNT_1-1)/2.),LED_COUNT_1).tolist()
  print(radius_list_1)
  strip1 = LED_strand(LED_COUNT_1, LED_PIN_1, LED_DMA_1, LED_ANGLE_1, radius_list_1)
  radius_list_2=np.linspace((LED_COUNT_2/2.),1,LED_COUNT_2/2).tolist() + np.linspace(-1,-1*(LED_COUNT_2/2.),LED_COUNT_2/2).tolist()
  print(radius_list_2)
  strip2 = LED_strand(LED_COUNT_2, LED_PIN_2, LED_DMA_2, LED_ANGLE_2, radius_list_2)
  strip1.begin()
  strip2.begin()
  led_strips = [strip1,strip2]
  angle_list = xrange(0,360,1)
  strip_led_count_list=[LED_COUNT_1,LED_COUNT_2]
  image_array = getImageArray('colors.png', LED_COUNT_1, LED_COUNT_1)
  angular_image = get_angular_image(image_array,angle_list,led_strips)
  print ('Press Ctrl-C to quit.')
  while True:
    sensor_data = get_sensor_data()
    if sensor_data[1]>90: #spinning fast enough
      theta = get_theta(sensor_data)
      pixel_colors = get_pixel_colors(angular_image, theta, sensor_data)
      processes=[]
      for strip_index in len(led_strips):
	new_process=Process(target=update_strips,args=(led_strips[strip_index],pixel_colors[strip_index],))
	processes.append(new_process)
	new_process.start()
      for process in processes:
	process.join()
    else:
      turn_off_leds(led_strips)

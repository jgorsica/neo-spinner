import math
import time
import numpy as np
import os.path
import pickle
import sys
import PIL
from PIL import Image
from multiprocessing import Process, Value
from led_strand import LED_strand
from icm_20601 import ICM_20601

DEG2RAD = math.pi/180.

# LED strand configuration:
LED_COUNT_1      = 144      # Number of LED pixels.
LED_PIN_1        = 18       # GPIO pin connected to the pixels (18 uses PWM).
LED_DMA_1        = 13       # DMA channel to use for generating signal
LED_CHANNEL_1    = 0        # PWM channel used
LED_ANGLE_1      = 0        # Relative angle between heads of LED strands

LED_COUNT_2      = 142      # Number of LED pixels.
LED_PIN_2        = 21       # GPIO pin connected to the pixels (21 uses SPI).
LED_DMA_2        = 14       # DMA channel to use for generating signal
LED_CHANNEL_2    = 0        # PWM channel, not used because SPI
LED_ANGLE_2      = 270      # Relative angle between heads of LED strands

I2C_BUS          = 1        # I2C bus that has motion sensor attached
SENSOR_ADDRESS   = 0x69     # I2C address of motion sensor (depends on how ADDRESS0 pin is connected)

TRIM_A           = 0        # Speed dependent angular error
TRIM_B           = 117       # Speed independent angular offset
NOISE_THRESHOLD  = 0.1      # Accel hysteresis (in g's), must be overcome at top and bottom of rotation

BILATERAL_INTERPOLATION = False    # When resampling image, use bilateral interpolation, otherwise lowest neighbor

'''Convert the provided red, green, blue color to a 24-bit color value.'''
def Color(red, green, blue, white = 0):
	return (white << 24) | (red << 16)| (green << 8) | blue

'''takes image file and produces array of RGBA pixel values for black padded, alpha blended image of correct size'''
def getImageArray(image_file, width, height):
	im = Image.open(image_file).convert('RGBA')
	im.thumbnail([height,width],Image.ANTIALIAS)
	im_width, im_height = im.size
	padded_thumb = Image.new('RGBA',(width, height), (0, 0, 0))
	paste_x_offset = (width-(im_width))//2
	paste_y_offset = (height-(im_height))//2
	paste_region = (paste_x_offset,paste_y_offset,paste_x_offset+im_width-1, \
			paste_y_offset+im_height-1)
	padded_thumb.paste(im, (paste_x_offset,paste_y_offset))
	background = Image.new('RGBA',[height,width],(0,0,0))
	alpha_composite = Image.alpha_composite(background,padded_thumb)
	alpha_composite.save('thumb.png')
	arr=np.array(alpha_composite)
	return arr[:,:,0:3]

'''Takes image pixel array and parameters describing physical LED strand configuration, 
      produces a precalculated array for each strand at each angle'''
def get_angular_image(filename,image_array,angle_list,strand):
  #Use pickle file if exists from previous use, otherwise generate new angular image
  fname = filename+"_"+str(strand.pin)+'.p'
  if os.path.isfile(fname) :
    f = open(fname, 'r')
    angular_image = pickle.load(f)
    f.close()
  else:
    angular_image=np.zeros((len(angle_list),strand.get_count()), dtype=np.int)
    #find largest radius to map to edge of square image
    radius = max([abs(x) for x in strand.get_radius_list()])
    led_count = strand.get_count()
    for theta in angle_list:
      #strand angular offset applied here, so that strands can use common theta reference
      cos_t = math.cos((theta+strand.get_theta())*DEG2RAD)
      sin_t = math.sin((theta+strand.get_theta())*DEG2RAD)
      for led_index in xrange(led_count):
        led_radius = strand.get_radius(led_index)
        x_r = led_radius * cos_t
        y_r = led_radius * sin_t
        #change origin from center to upper left
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
        if BILATERAL_INTERPOLATION:
          #get four closest pixels and bilaterally interpolate
          p11=image_array[x1,y1]
          p21=image_array[x2,y1]
          p12=image_array[x1,y2]
          p22=image_array[x2,y2]
          p=(y-y2)*(x-x1)*p21+(x2-x)*(y-y2)*p11+(y1-y)*(x-x1)*p22+(x2-x)*(y1-y)*p12
          color=Color(int(p[0]),int(p[1]),int(p[2]))
        else: #lowest neighbor
          p=image_array[x1,y2]
          color=Color(p[0],p[1],p[2])
        angular_image[theta,led_index]=color
    f = open(fname, 'w')
    pickle.dump(angular_image, f)
    f.close()
  return angular_image
  
def get_sensor_data(sensor):
  ts, accel, gyro = sensor.get_sensor_data_bare()
  return [ts,accel,-1*gyro]
  
'''uses sensor data to determine exact angular position of the spinner'''
prev_theta = 0 #angle of rotation, 0 = up
y_dir = 0 #trend of accel_y data
y_prev_dir=0 #previous_trend of accel_y data
y_prev=0 #previous accel_y_data
prev_ts=0 #previous timestamp
y_min=0
y_max=0
armed=False
def get_theta(sensor_data):
  global prev_theta, y_dir, y_prev_dir, y_prev, prev_ts, y_min, y_max, armed
  v=sensor_data[2] # rotational velocity, degrees per second in clockwise direction
  y=sensor_data[1] # accel_y in g's
  ts=sensor_data[0] # timestamp in seconds
  # If long time between updates, reset everything
  if (ts-prev_ts) > 5:
    prev_ts = ts
    y_prev = y
    y_prev_dir = 0
    y_dir = 0
  theta = prev_theta + v*(ts-prev_ts)
  while theta>=360:
    theta -= 360
  while theta<0:
    theta += 360
  # Use accelerometer data track gravity rotation, mark top and bottom of rotation
  if (y-y_prev)>NOISE_THRESHOLD:
    y_dir=1 #up
    y_prev=y
  elif (y_prev-y)>NOISE_THRESHOLD:
    y_dir=-1 #down
    y_prev=y
  if (y_dir==-1 and y_prev_dir==1): #top
    y_max=y
    armed=True
  elif (y_dir==1 and y_prev_dir==-1): #bottom
    y_min=y
  # Use event of passing point between top and bottom as trigger to reset theta
  if y<((y_max-y_min)/2.) and armed: #right side
    offset=TRIM_A*v+TRIM_B
    if abs(theta-offset)<=180:
      theta=theta*0.7+offset*0.3
    elif (theta-offset)>180:
      theta-=360
      theta=theta*0.7+offset*0.3
      if theta<0:
        theta += 360
    else:
      offset-=360
      theta=theta*0.7+offset*0.3
      if theta<0:
        theta += 360
    armed=False
  prev_ts=ts
  y_prev_dir=y_dir
  prev_theta = theta
  return int(theta)

def turn_off_leds(led_strands):
  for strand in led_strands:
	for led_index in xrange(strand.get_count()):
		strand.setPixelColor(led_index, 0)
	strand.show()
	
def update_strand(strand, pixel_colors_by_angle, theta, spin_rate):
  #time1=time.time()
  count=strand.get_count()
  pixel_updates_per_degree = min(int(1/0.00003/spin_rate),count)
  pointer=0
  pixels_at_angle=[]
  while pointer<count:
    last=min(count, pointer+pixel_updates_per_degree)
    pixels_at_angle.extend(pixel_colors_by_angle[theta,pointer:last])
    pointer += pixel_updates_per_degree
    theta += 1
    if theta==360:
      theta=0
  strand.setPixelColor(slice(0,count),pixels_at_angle)
  #time2=time.time()
  strand.show()
  #time3=time.time()
  #print("time setting pixels: "+str(time2-time1)+" seconds, time to show: "+str(time3-time2)+" seconds")
	
def update_loop(strand, image_filename, image_array, angle_list, theta_received, spin_rate_received, stop_request_received):
  print('getting angular image...')
  pixel_colors_by_angle = get_angular_image(image_filename,image_array,angle_list,strand)
  update_count = 0
  print('starting updates...')
  while stop_request_received.value==0:
    #do we need a per pixel rotation offset?
    #pixels = get_pixel_colors(pixel_colors_by_angle, theta_received.value, spin_rate_received.value)
    update_strand(strand, pixel_colors_by_angle, theta_received.value, spin_rate_received.value)
  turn_off_leds([strand])
	
def start(image_filename):
  sensor = ICM_20601(I2C_BUS, SENSOR_ADDRESS)
  '''initialize strands'''
  #evenly spaced even number of LEDs
  radius_list_1=np.linspace((LED_COUNT_1-1)/2.,-1*((LED_COUNT_1-1)/2.),LED_COUNT_1).tolist()
  strand1 = LED_strand(LED_COUNT_1, LED_PIN_1, LED_DMA_1, LED_ANGLE_1, radius_list_1, channel=LED_CHANNEL_1)
  #evenly spaced even number of LEDs with 1 LED gap in middle
  radius_list_2=np.linspace((LED_COUNT_2/2.),1,LED_COUNT_2/2).tolist() + np.linspace(-1,-1*(LED_COUNT_2/2.),LED_COUNT_2/2).tolist()
  strand2 = LED_strand(LED_COUNT_2, LED_PIN_2, LED_DMA_2, LED_ANGLE_2, radius_list_2, channel=LED_CHANNEL_2)
  strand1.begin()
  strand2.begin()
  print('strands initialized')
  led_strands = [strand1,strand2]
  angle_list = xrange(0,360,1) #used as array index, so not easily changed
  print('getting image array...')
  image_array = getImageArray(image_filename, LED_COUNT_1, LED_COUNT_1)
  #create variables in shared memory to pass new theta and spin rate values to processes running update loops
  theta_to_pass = Value('i', 0)
  spin_rate_to_pass = Value('d',0)
  stop_request_to_pass = Value('i',0)
  print ('Starting process for each strand, Press Ctrl-C to quit.')
  processes=[]
  for strand_index in xrange(len(led_strands)):
    new_process=Process(target=update_loop,args=(led_strands[strand_index], image_filename, image_array, angle_list, \
                                                 theta_to_pass, spin_rate_to_pass, stop_request_to_pass))
    processes.append(new_process)
    new_process.start()
  #start loop to get new sensor data, compute angle of rotation, and update other processes
  while stop_request_to_pass.value==0:
    sensor_data = get_sensor_data(sensor)
    #print(sensor_data)
    spin_rate_to_pass.value=sensor_data[2]
    if abs(sensor_data[2])>5: #spinning fast enough
      theta_to_pass.value = get_theta(sensor_data)
    else:
      stop_request_to_pass.value = 1
    time.sleep(0.001)
  for process in processes:
      process.join()
    
  
if __name__ == '__main__':
  start(sys.argv[1])

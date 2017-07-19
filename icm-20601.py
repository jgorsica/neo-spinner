import smbus

class ICM-20601(object):
     self.GYRO_Z_OFFSET_REG = 0x18
     self.CONFIG_REG = 0x1A
     self.CONFIG = 0x06 # Gyro Rate 1KHz, heavily filtered
     self.GYRO_CONFIG_REG = 0x1B
     self.GYRO_CONFIG = 0x18 # +/-4000dps
     self.GYRO_RANGE = 8000. #dps/16-bit value
     self.GYRO_SCALE = GYRO_RANGE / 256 / 256
     self.ACCEL_CONFIG_REG = 0x1C
     self.ACCEL_CONFIG = 0x00 # +/-4g
     self.ACCEL_RANGE = 8. #g/16-bit value
     self.ACCEL_SCALE = ACCEL_RANGE / 256 / 256
     self.ACCEL_CONFIG2_REG = 0x1D
     self.ACCEL_CONFIG2 = 0x00 # Accel Rate 1KHz, lightly filtered
     self.LP_MODE_CONFIG_REG = 0x1E
     self.LP_MODE_CONFIG = 0x00 # Disable Gyro Low-Power Mode
     self.FIFO_ENABLE_REG = 0x23
     self.FIFO_ENABLE = 0x00 # All FIFOs disabled
     self.INT_ENABLE_REG = 0x38
     self.INT_ENABLE = 0x00 # Disable all interrupts
     self.USER_CONTROL_REG = 0x6A
     self.USER_CONTROL = 0x00 # Disables FIFO Access
     self.PWR_MAN1_REG = 0x6B
     self.PWR_MAN1 = 0x01 # Use PLL as CLK Input
     self.PWR_MAN2_REG = 0x6C
     self.PWR_MAN2 = 0x00 # All sensor channels on
     self.WHOAMI_REG = 0x75
     self.WHOIAM = 0xAC
     self.SENSOR_OUT_14_BYTE_REG = 0x3B #AXH, AXL, AYH, AYL, AZH, AZL, TH, TL, GXH, GXL, GYH, GYL, GZH, GZL
     self.TEMP_SCALE = 1 / 326.8

     def __init__(self,bus_number=1,address=0x69):
          self.bus = smbus.SMBus(bus_number)
          self.i2c_address=address
          if check_interface():
               print('interface working')
          else:
               print('interface not working')
               quit()
          self.init_registers()

     def write(self, address, data):
          self.bus.write_byte_data(self.i2c_address, address, data)

     def read(self, address):
          byte = self.bus.read_byte_data(self.i2c_address, address)
          print(byte)
          return byte

     def read_bytes(self, address, count):
          return self.bus.read_i2c_block_data(self.i2c_address, address, count)
     
     def init_registers(self):
          self.write(self.CONFIG_REG, self.CONFIG)
          self.write(self.GYRO_CONFIG_REG, self.GYRO_CONFIG)
          self.write(self.ACCEL_CONFIG_REG, self.ACCEL_CONFIG)
          self.write(self.ACCEL_CONFIG2_REG, self.ACCEL_CONFIG2)
          self.write(self.LP_MODE_CONFIG_REG, self.LP_MODE_CONFIG)
          self.write(self.FIFO_ENABLE_REG, self.FIFO_ENABLE)
          self.write(self.INT_ENABLE_REG, self.INT_ENABLE)
          self.write(self.USER_CONTROL_REG, self.USER_CONTROL)
          self.write(self.PWR_MAN1_REG, self.PWR_MAN1)
          self.write(self.PWR_MAN2_REG, self.PWR_MAN2)
     
     def check_interface(self):
          return self.WHOIAM == self.read(self.WHOAMI_REG)
     
     def get_sensor_data(self):
          data=self.read_bytes(self.SENSOR_OUT_14_BYTE_REG, 14)
          accel_data_counts=[(data[0]<<8)|data[1],(data[2]<<8)|data[3],(data[4]<<8)|data[5]]
          accel_data=[]
          accel_data.append(accel_data_counts[0] * self.ACCEL_SCALE)
          accel_data.append(accel_data_counts[1] * self.ACCEL_SCALE)
          accel_data.append(accel_data_counts[2] * self.ACCEL_SCALE)
          for i in xrange(len(accel_data)):
               if accel_data[i]>self.ACCEL_RANGE/2:
                    accel_data[i] -= self.ACCEL_RANGE
          temp_data_counts=(data[6]<<8)|data[7]
          temp_data=temp_data_counts * self.TEMP_SCALE
          gyro_data_counts=[(data[8]<<8)|data[9],(data[10]<<8)|data[11],(data[12]<<8)|data[13]]
          gyro_data=[]
          gyro_data.append(gyro_data_counts[0] * self.GYRO_SCALE)
          gyro_data.append(gyro_data_counts[1] * self.GYRO_SCALE)
          gyro_data.append(gyro_data_counts[2] * self.GYRO_SCALE)
          for i in xrange(len(gyro_data)):
               if gyro_data[i] > self.GYRO_RANGE/2:
                    gyro_data[i] -= self.GYRO_RANGE
          print(str(accel_data)+','+str(temp_data)+','+str(gyro_data))
          return accel_data, gyro_data, temp_data

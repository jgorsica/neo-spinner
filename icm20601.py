import smbus

I2C_BUS = 1
I2C_ADDRESS = 0x69
GYRO_Z_OFFSET_REG = 0x18
CONFIG_REG = 0x1A
CONFIG = 0x06 # Gyro Rate 1KHz, heavily filtered
GYRO_CONFIG_REG = 0x1B
GYRO_CONFIG = 0x18 # +/-4000dps
GYRO_RANGE = 8000. #dps/16-bit value
GYRO_SCALE = GYRO_RANGE / 256 / 256
ACCEL_CONFIG_REG = 0x1C
ACCEL_CONFIG = 0x00 # +/-4g
ACCEL_RANGE = 8. #g/16-bit value
ACCEL_SCALE = ACCEL_RANGE / 256 / 256
ACCEL_CONFIG2_REG = 0x1D
ACCEL_CONFIG2 = 0x00 # Accel Rate 1KHz, lightly filtered
LP_MODE_CONFIG_REG = 0x1E
LP_MODE_CONFIG = 0x00 # Disable Gyro Low-Power Mode
FIFO_ENABLE_REG = 0x23
FIFO_ENABLE = 0x00 # All FIFOs disabled
INT_ENABLE_REG = 0x38
INT_ENABLE = 0x00 # Disable all interrupts
USER_CONTROL_REG = 0x6A
USER_CONTROL = 0x00 # Disables FIFO Access
PWR_MAN1_REG = 0x6B
PWR_MAN1 = 0x01 # Use PLL as CLK Input
PWR_MAN2_REG = 0x6C
PWR_Man2 = 0x00 # All sensor channels on
WHOAMI_REG = 0x75
WHOIAM = 0xAC
SENSOR_OUT_14_BYTE_REG = 0x3B #AXH, AXL, AYH, AYL, AZH, AZL, TH, TL, GXH, GXL, GYH, GYL, GZH, GZL
TEMP_SCALE = 1 / 326.8

def write(address, data):
     with smbus.SMBus(I2C_BUS) as bus:
          bus.write_byte_data(I2C_ADDRESS, address, data)
     
def read(address):
     with smbus.SMBus(I2C_BUS) as bus:
          return bus.read_byte_data(I2C_ADDRESS, address)
     
def read_bytes(address, count):
     with smbus.SMBus(I2C_BUS) as bus:
          return bus.read_i2c_block_data(I2C_ADDRESS, address, count)
     
def init_registers():
     write(CONFIG_REG, CONFIG)
     write(GYRO_CONFIG_REG, GYRO_CONFIG)
     write(ACCEL_CONFIG1_REG, ACCEL_CONFIG1)
     write(ACCEL_CONFIG2_REG, ACCEL_CONFIG2)
     write(LP_MODE_CONFIG_REG, LP_MODE_CONFIG)
     write(FIFO_ENABLE_REG, FIFO_ENABLE)
     write(INT_ENABLE_REG, INT_ENABLE)
     write(USER_CONTROL_REG, USER_CONTROL)
     write(PWR_MAN1_REG, PWR_MAN1)
     write(PWR_MAN2_REG, PWR_MAN2)
     
def check_interface():
     return WHOIAM == read(WHOAMI_REG)
     
def get_sensor_data():
     data=read_bytes(SENSOR_OUT_14_BYTE_REG, 14)
     accel_data_counts=[(data[0]<<8)|data[1],(data[2]<<8)|data[3],(data[4]<<8)|data[5]]
     accel_data=[]
     accel_data.append(accel_data_counts[0] * ACCEL_SCALE)
     accel_data.append(accel_data_counts[1] * ACCEL_SCALE)
     accel_data.append(accel_data_counts[2] * ACCEL_SCALE)
     temp_data_counts=(data[6]<<8)|data[7]
     temp_data=temp_data_counts * TEMP_SCALE
     gyro_data_counts=[(data[8]<<8)|data[9],(data[10]<<8)|data[11],(data[12]<<8)|data[13]]
     gyro_data=[]
     gyro_data.append(gyro_data_counts[0] * GYRO_SCALE)
     gyro_data.append(gyro_data_counts[1] * GYRO_SCALE)
     gyro_data.append(gyro_data_counts[2] * GYRO_SCALE)
     print(str(accel_data)+','+str(temp_data)+','+str(gyro_data))
     return accel_data, gyro_data, temp_data
     
if __name__ == "__main__":
     if check_interface():
          print('interface working')
     else:
          print('interface not working')
          exit()
     init_registers()
     a, g, t = get_sensor_data()
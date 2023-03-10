#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# to do: - reconnect when connection closes
import serial, time, os, sys, datetime, mariadb, logging
from config import *

ttyPORT = '/dev/ttyUSB0' if os.path.exists('/dev/ttyUSB0') else '/dev/ttyACM0';

# init db connections
try:
    conn = mariadb.connect(
            user=DB_USER,
	    password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_SCHEMA)
    cursor = conn.cursor()
except mariadb.Error as e:
    logger.info(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

# Read from ttyPORT
def read (arduino):
    time.sleep(0.1)
    # logger.info('Reading...')
    while arduino.inWaiting() == 0:
        time.sleep(0.1)
        pass
    if arduino.inWaiting() > 0:
        msg = arduino.readline()
        if (not msg): pass

        dataMsg = str(msg.decode('utf-8').rstrip())
        # logger.info(dataMsg)
        arduino.flushInput() #remove data after reading
        temp, hum = dataMsg.split(',')
        # logger.info(f'Temperature: {temp}, Humidity: {hum}')
        saveToDB(temp, hum)

# store observations in DB
def saveToDB (temp, hum):
    minutes = datetime.datetime.now().minute 
    # nos quedamos solo con valores de en punto e y media
    if ((minutes >= 0 and minutes <= 10) or (minutes >= 30 and minutes <= 40)):
        try:
            cursor.execute("INSERT INTO observations(date, temperature, humidity) VALUES (now(), ?, ?);", (temp, hum))  
        except mariadb.Error as e:
            logger.info(f"Error: {e}")

# returns max and min temperature values from the last 24h
def getMinMaxTemp ():
    try:
        cursor.execute("SELECT format(min(temperature), 1) AS max, format(max(temperature), 1) AS min FROM observations WHERE date > now() - interval 24 hour;")
        for minTemp, maxTemp in cursor:
            return { 'min': minTemp, 'max': maxTemp }
    except mariadb.Error as e:
        logger.info(f"Error: {f}")

# main function
if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    logger = logging.getLogger(__name__)

    if not os.path.exists(ttyPORT):
        logger.info('No arduino connected! Going out...')
        exit(0)
    logger.info('Running. Press CTRL-C to exit.')

    with serial.Serial(ttyPORT, 9600, timeout=1) as arduino:
        arduino.flush()
        time.sleep(0.1) #wait for serial to open
        if arduino.isOpen():
            logger.info("{} connected!".format(arduino.port))
            try:
                while True:
                    read(arduino) # dentro hay un sleep
                    minMax = getMinMaxTemp()
                    min = minMax['min']
                    max = minMax['max']
                    msg = f'{min},{max}'
                    # logger.info(f'Sending to arduino "{msg}"')
                    arduino.write(msg.encode())
                                                        
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt has been caught.")
                conn.close()

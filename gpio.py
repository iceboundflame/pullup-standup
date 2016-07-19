#!/usr/bin/env python

# BCM 12 = Data 0
# BCM 13 = Data 1
# BCM 5 = Beeper
# BCM 6 = Green LED

import time
import pigpio
import wiegand
import Adafruit_ADS1x15

adc = Adafruit_ADS1x15.ADS1115()
#  -   1 = +/-4.096V
#  -   2 = +/-2.048V
ADC_GAIN = 1

BEEPER_PIN = 5
GREEN_PIN = 6
DATA_0_PIN = 12
DATA_1_PIN = 13

pi = pigpio.pi()
green = False

pi.set_mode(BEEPER_PIN, pigpio.OUTPUT)
pi.set_mode(GREEN_PIN, pigpio.OUTPUT)
pi.write(BEEPER_PIN, 1)
pi.write(GREEN_PIN, 1)


def callback(bits, code):
    print("bits={} code={}".format(bits, code))
    global green
    green = not green
    pi.write(GREEN_PIN, 0 if green else 1)

    pi.write(BEEPER_PIN, 0)
    time.sleep(0.5)
    pi.write(BEEPER_PIN, 1)

w = wiegand.decoder(pi, DATA_0_PIN, DATA_1_PIN, callback)


# Read channel 0 for 5 seconds and print out its values.
while True:
    value = adc.read_adc(0, gain=ADC_GAIN, data_rate=8)
    print('{0}'.format(value))
    # Sleep for half a second.
    time.sleep(0.1)

# Stop continuous conversion.  After this point you can't get data from get_last_result!
adc.stop_adc()
w.cancel()
pi.stop()

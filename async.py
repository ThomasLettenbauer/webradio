import asyncio, evdev
import alsaaudio
import RPi.GPIO as GPIO
from mpg123 import Mpg123, Out123
import time
import os
from gtts import gTTS
from io import BytesIO
from mpd import MPDClient

m = alsaaudio.Mixer()
# m.setvolume(50) # Set audio for tts output

client = MPDClient();
client.connect("localhost", 6600);

volume_dial = evdev.InputDevice('/dev/input/by-path/platform-rotary@5-event')
station_dial = evdev.InputDevice('/dev/input/by-path/platform-rotary@16-event')

try:
    volume = int(client.status()["volume"]);
except:
    print ("error getting volume from client")
    print (client.status())
    volume = 20 

client.setvol(volume)
m.setvolume(volume + 10) # Set audio for tts output

station = 0
station_num = 5

LED_A = 23
LED_B = 24

# initialize GPIO for LEDs
def led_init():
    GPIO.setwarnings(True)
    GPIO.setmode(GPIO.BCM)  # Use BCM mode
    
    # define the LED outputs
    GPIO.setup(LED_A, GPIO.OUT) 
    GPIO.setup(LED_B, GPIO.OUT)

    # LEDs off per default
    GPIO.output(LED_A, GPIO.LOW)
    GPIO.output(LED_B, GPIO.LOW)
    
    return

# Switch LEDs On
def led_on():
    GPIO.output(LED_A, GPIO.HIGH)
    GPIO.output(LED_B, GPIO.HIGH)

# Switch LEDs Off
def led_off():
    GPIO.output(LED_A, GPIO.LOW)
    GPIO.output(LED_B, GPIO.LOW)

# say the station name
def say_station(station):
    try:
        station_name = client.playlistinfo()[station]["name"]
    except:
        station_name = "Sender Nummer " + str(station)

    print("Station: " + station_name)

    mp3_fp = BytesIO()
    tts = gTTS(station_name, lang='de')
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)

    #-- - play it-- -

    mp3 = Mpg123()
    mp3.feed(mp3_fp.read())

    out = Out123()

    time.sleep(0.1)

    for frame in mp3.iter_frames(out.start):
        out.play(frame)

async def process_events(device):

    global client, volume, station, station_num, m
    
    async for event in device.async_read_loop():

        if device == volume_dial and event.type == evdev.ecodes.EV_REL:
            volume += event.value
            if volume < 0:
                volume = 0
            elif volume > 100:
                volume= 100
            print("Volume: " + str(volume))
            client.setvol(volume)
            m.setvolume(volume + 10)

        if device == station_dial and event.type == evdev.ecodes.EV_REL:

            station += event.value
            if station < 0:
                station = station_num - 1
            elif station > station_num - 1:
                station = 0

            say_station(station)

            #empty event queue
            while device.read_one() != None:
                pass

            print("sleeping - wait for events...")        
            time.sleep(1) #Wait for more events

            print("now play station...")

            #No event happened in sleep time -> set new station
            if device.read_one() == None:
                client.play(station)

            while device.read_one() != None:
                            pass


led_init()
led_on()

say_station(station)
client.play(station)



for device in volume_dial, station_dial:
    asyncio.ensure_future(process_events(device))

loop = asyncio.get_event_loop()
loop.run_forever()

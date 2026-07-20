
import os
import struct
import asyncio
import time
import array
import gc
import json
import math

from microdot import Microdot, Response, send_file
from aw9523 import AW9523
from as7343 import AS7343
import npyfile

import processing

# Free memory used by imports
gc.collect()

async def measure_one(as7343, data, offset=0, wait_time=1.0):

    order = AS7343.CHANNEL_MAP

    # wait for condition to settle
    await asyncio.sleep(wait_time)

    # XXX: make sure to flush out old readings from FIFO
    for i in range(10):
        readings = as7343.read()
        await asyncio.sleep(0.10)

    # Copy data
    for i, c in enumerate(order):
        data[offset+i] = readings[c]

    await asyncio.sleep(wait_time)

async def measure_sample(i2c_ext, ext, data, wait_time=1.0):
    """
    Make one complete measurement, consisting of 3 sub-measurements:

    - no excitation / baseline
    - UV excitation / flouresence
    - white / reflectance

    The values are concatenated
    """
    
    as7343 = AS7343(i2c_ext)

    as7343.set_measurement_time(200) # ms
    as7343.set_integration_time(100*1000, repeat=1) # us
    as7343.set_illumination_led(False)
    as7343.set_illumination_current(4)

    n_channels = len(AS7343.CHANNEL_MAP)
    n_datapoints = n_channels * 3
    assert len(data) == n_datapoints

    start = time.ticks_ms()
    print('measure-sample-start', start)

    as7343.start_measurement()
    await asyncio.sleep(0.1)   

    # measure without exitation
    #print('measure-no-light')
    #ext[0:16] = 0
    #await measure_one(as7343, data, offset=0, wait_time=wait_time)

    # Measure with UV exitation
    print('measure-uv')
    ext[0:16] = 100
    await measure_one(as7343, data, offset=n_channels, wait_time=wait_time)
    ext[0:16] = 0

    # Measure with white LED
    #print('measure-white')
    #as7343.set_illumination_led(True)
    #await measure_one(as7343, data, offset=2*n_channels, wait_time=wait_time)
    #as7343.set_illumination_led(False)

    as7343.stop_measurement()

    duration = time.ticks_diff(time.ticks_ms(), start)
    print('measure-sample-end', time.ticks_ms(), duration)


# ---------------------------------------------------------------------------
# WiFi
# ---------------------------------------------------------------------------

async def _connect_wifi():
    """Connect to WiFi using credentials from secrets.py.
    No-op on non-device platforms where the network module is unavailable."""
    try:
        import network
    except ImportError:
        return

    import secrets

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print('WiFi already connected:', wlan.ifconfig()[0])
        return

    print('Connecting to WiFi SSID: {} ...'.format(secrets.SSID))
    wlan.connect(secrets.SSID, secrets.PASSWORD)

    while not wlan.isconnected():
        await asyncio.sleep(0.5)

    print('WiFi connected:', wlan.ifconfig()[0])


# TODO: track whether measuring or not
class State:
    def __init__(self, i2c, ext):
        self.i2c = i2c
        self.ext = ext

def add_routes(app, state):

    # User interface
    MAX_AGE = 1 # XXX: set longer in production, for more efficient caching

    @app.get('/')
    async def get_index(request):
        return send_file('frontend/index.html')

    @app.get('/static/<path:path>')
    async def get_static(request, path):
        return send_file('frontend/' + path, max_age=MAX_AGE)

    @app.get('/samples.json')
    async def get_samples(request):
        samples = []

        path = 'data/try2/data3/'
        for s in processing.load_samples(path):
            samples.append(s)

        return samples, 200

    @app.get('/status')
    async def get_status(request):
        s = {
            'connected': True,            
            'measuring': True,
            'progress': 50,
        }
        return s, 200

    @app.post('/measure')
    async def post_measure(request, path):

        # Trigger a measurement
        # TODO: error if something is already in progress. CONFLICT
        # TODO: do async.
        # Start the measurement, and track progress in some object.
        data = array.array('f', (0.0 for _ in range(3*len(AS7343.CHANNEL_MAP))))
        await measure_sample(state.i2c_ext, state.ext, data=data, wait_time=0.2)

        out = {}
        return out, 200


def main(host='0.0.0.0', port=8000, debug=True):

    print('app-load')

    # Web server
    app = Microdot()

    i2c_ext = None
    ext = None
    if False: # TODO: detect when on device
        from machine import Pin, I2C
        i2c_ext = I2C(1, scl=Pin(5), sda=Pin(4), freq=400000)
        as7343 = AS7343(i2c_ext)
        ext = AW9523(i2c_ext, address=0x5b)

    state = State(i2c=i2c_ext, ext=ext)

    from cors import CORS
    cors = CORS(app, allowed_origins='*', allow_credentials=False)

    add_routes(app, state)

    # Reduce memory pressure
    gc.collect()
    print('app-start', 'mem_free={}'.format(gc.mem_free()))

    # Actually start server
    async def _startup():
        await _connect_wifi()
        print('HTTP server on {}:{}'.format(host, port))
        await app.start_server(host=host, port=port, debug=debug)

    asyncio.run(_startup())

if __name__ == '__main__':
    main()


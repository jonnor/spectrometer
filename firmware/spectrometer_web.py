
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
from measure import MeasurementService

# Free memory used by imports
gc.collect()


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
        progress_percent = 100*state.measurement.get_progress()
        s = {
            'connected': True,            
            'measuring': state.measurement.is_started(),
            'progress': progress_percent,
        }
        return s, 200

    @app.post('/measure')
    async def post_measure(request):

        # Trigger a measurement
        # will cause exception if multiple. TODO: convert to exception
        state.measurement.start()

        out = {}
        return out, 200


class AppState:
    def __init__(self, measurement):
        self.measurement = measurement


def main(host='0.0.0.0', port=8000, debug=True):

    print('app-load')

    # Web server
    app = Microdot()

    i2c = None
    gpio = None
    as7343 = None
    if False: # TODO: detect when on device
        from machine import Pin, I2C
        i2c = I2C(1, scl=Pin(5), sda=Pin(4), freq=400000)
        as7343 = AS7343(i2c_ext)
        gpio = AW9523(i2c_ext, address=0x5b)

    state = AppState(measurement=MeasurementService(as7343, gpio))

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


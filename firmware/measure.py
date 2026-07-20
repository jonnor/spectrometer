
import array
import asyncio
import time

from aw9523 import AW9523
from as7343 import AS7343

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

async def measure_sample(as7343, ext, data, wait_time=1.0):
    """
    Make one complete measurement, consisting of 3 sub-measurements:

    - no excitation / baseline
    - UV excitation / flouresence
    - white / reflectance

    The values are concatenated
    """

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
    print('measure-no-light')
    ext[0:16] = 0
    await measure_one(as7343, data, offset=0, wait_time=wait_time)

    # Measure with UV exitation
    print('measure-uv')
    ext[0:16] = 100
    await measure_one(as7343, data, offset=n_channels, wait_time=wait_time)
    ext[0:16] = 0

    # Measure with white LED
    print('measure-white')
    as7343.set_illumination_led(True)
    await measure_one(as7343, data, offset=2*n_channels, wait_time=wait_time)
    as7343.set_illumination_led(False)

    as7343.stop_measurement()

    duration = time.ticks_diff(time.ticks_ms(), start)
    print('measure-sample-end', time.ticks_ms(), duration)

    return duration

def measure_sample_dummy(data, wait_time=1.0):
    """
    Pretend to measure - useful on PC when developing
    """

    start = time.ticks_ms()
    print('dummy-measure-sample-start', start)
    await asyncio.sleep(1.0 + (2*3*wait_time))
    duration = time.ticks_diff(time.ticks_ms(), start)
    print('dummy-measure-sample-start', time.ticks_ms(), duration)

class MeasurementAlreadyStarted(ValueError):
    def __init__(self):
        super().__init__("Cannot run multiple measurements at same time")


# FIXME: add a way to get the data on completion. Maybe a queue? or a callback function.
# Who writes to disk?
class MeasurementService:
    """
    Keep track of a single measurement task
    """

    def __init__(self, aw=None, gpio=None, wait_per_round=1.0):
        self._started_at = None
        self._task = None
        self._aw = aw
        self._gpio = gpio
        self._data = array.array('f', (0.0 for _ in range(3*len(AS7343.CHANNEL_MAP))))
        self._wait_per_round = wait_per_round

    def start(self):
        # check pre-conditions        
        if self.is_started():
            raise MeasurementAlreadyStarted()
        assert self._task is None

        # Start the task in background
        if self._aw is None or self._gpio is None:
            coro = measure_sample_dummy(self._data, wait_time=self._wait_per_round)
        else:
            coro = measure_sample(self._aw, self._gpio, self._data, wait_time=self._wait_per_round)

        self._task = asyncio.create_task(coro)
        self._started_at = time.ticks_ms()

        # check post-conditions
        assert self.is_started()
        assert not self._task.done()

    def get_expected_duration(self):
        d = 1.0 + (3*2 * (self._wait_per_round+1.0))
        return d

    def get_progress(self):
        """
        Note: this is an estimate
        """
        if not self.is_started():
            return 0.0

        since_start = time.ticks_diff(time.ticks_ms(), self._started_at) / 1000.0
        expect_duration = self.get_expected_duration()

        progress = since_start / expect_duration

        progress = max(0.0, progress)
        progress = min(1.0, progress)
        return progress

    def is_started(self):
        # check if we are in fact done, and if so, update internal state
        if self._task is not None and self._task.done():
            # XXX: no result(). But this should return immediately
            assert self._started_at is not None # invariant, always set if _task
            #actual_duration = self._task 
            #ex = self.get_expected_duration()
            print('measurement-task-done')
            self._task = None
            self._started_at = None

        return self._started_at is not None


import threading
import time


class RateLimiter:

    def __init__(self, interval: float):
        self.interval = interval
        self.lock = threading.Lock()
        self.last_time = 0.0

    def acquire(self):
        with self.lock:
            now = time.time()
            diff = now - self.last_time
            if diff < self.interval:
                time.sleep(self.interval - diff)
            self.last_time = time.time()


rate_limiter = RateLimiter(interval=0.3)

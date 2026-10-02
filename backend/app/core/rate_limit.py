import time
from collections import defaultdict
from threading import Lock

class RateLimiter:
    def __init__(self):
        # Maps IP to list of timestamps
        self.ip_records = defaultdict(list)
        # Maps API Key to list of timestamps
        self.key_records = defaultdict(list)
        # Tracks global count for today
        self.global_daily_count = 0
        self.current_global_day = self._get_current_day()
        self.lock = Lock()

    def _get_current_day(self):
        return time.time() // 86400

    def check_ip_limit(self, ip: str, limit: int, window_seconds: int = 60) -> int:
        """Returns retry_after in seconds if exceeded, else 0."""
        with self.lock:
            now = time.time()
            cutoff = now - window_seconds
            # Cleanup old records
            self.ip_records[ip] = [ts for ts in self.ip_records[ip] if ts > cutoff]
            if len(self.ip_records[ip]) >= limit:
                # Calculate retry after based on the oldest timestamp in the window
                retry_after = int(self.ip_records[ip][0] + window_seconds - now)
                return max(1, retry_after)
            self.ip_records[ip].append(now)
            return 0

    def check_key_limit(self, key: str, limit: int, window_seconds: int = 86400) -> int:
        with self.lock:
            now = time.time()
            cutoff = now - window_seconds
            self.key_records[key] = [ts for ts in self.key_records[key] if ts > cutoff]
            if len(self.key_records[key]) >= limit:
                retry_after = int(self.key_records[key][0] + window_seconds - now)
                return max(1, retry_after)
            self.key_records[key].append(now)
            return 0
            
    def check_global_daily_limit(self, limit: int) -> bool:
        """Returns True if within limit, False if exceeded."""
        with self.lock:
            today = self._get_current_day()
            if self.current_global_day != today:
                self.current_global_day = today
                self.global_daily_count = 0
                
            if self.global_daily_count >= limit:
                return False
                
            self.global_daily_count += 1
            return True

limiter = RateLimiter()

"""Manages Hosts Running Jobs"""
from env_store import EnvStore

class Hosts():
    """Class hosts running jobs"""

    def __init__(self, file):
        """setup datacenter configuration like regions"""
        self.datacenter_config = EnvStore(file)
        self.host_count = None

    def set_count(self, count):
        """update host count"""
        self.host_count = count

    def has_hosts(self):
        """boolean indicating allocated hosts"""
        if self.host_count > 0:
            return True
        return False

"""Module provides persists and retrieves error logs.
"""
import os
import html
import shutil
from pathlib import Path

class ErrorLog:
    """
    Posted Error Logs from replay hosts persisted to filesystem
    Logs can be retreived as well.
    """
    def __init__(self, log_dir):
        # Check if output directory exists, if not, create it
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.log_dir = log_dir
        self.has_free_space = True

        # Get the disk usage statistics
        usage = shutil.disk_usage(self.log_dir)

        # Check Free Space
        if usage.used/usage.total > 0.98:
            self.has_free_space = False

    @staticmethod
    def file_name(log_dir,jobid,log_type):
        """constructs file name as static method"""
        return f'{log_dir}/{log_type}{jobid}.log'

    @staticmethod
    def clean_all(log_dir):
        """removes all the old logs"""
        dir_path = Path(log_dir)
        if dir_path.exists() and dir_path.is_dir():
            shutil.rmtree(dir_path)

    def persist(self,jobid,log_type,data):
        """write log to disk"""

        # no free space abort
        if not self.has_free_space:
            return False

        file_name = ErrorLog.file_name(self.log_dir,jobid,log_type)
        with open(file_name, "w", encoding='utf-8') as file:
            file.write(html.escape(data))
        return True

    def retrieve(self,jobid,log_type):
        """read from disk"""

        file_name = ErrorLog.file_name(self.log_dir,jobid,log_type)
        contents = None

        if not os.path.exists(file_name):
            return None

        with open(file_name, 'r', encoding='utf-8') as file:
            contents = file.read()
        return contents

"""Module writes and puts env vars"""
import sys
import os

class EnvStore():
    """Class to manage env vars"""

    def __init__(self, file):
        """initialize from file"""
        self.env_name_values = {}
        if os.path.exists(file):
            with open('env', 'r', encoding='utf-8') as properties_file:
                # Read and parse each line into a list of tuples (name, value)
                for line in properties_file:
                    line = line.strip()
                    # Skip empty lines
                    if not line:
                        continue
                    # Assuming the line format is "name=value" or "name:value"
                    if '=' in line:
                        name, value = line.split('=', 1)
                    elif ':' in line:
                        name, value = line.split(':', 1)
                    else:
                        print(f"Line format in env file not recognized: {line}")
                        continue
                    self.env_name_values[name.strip()] = value.strip()
        else:
            sys.exit(f"Can't find file {file} in current directory, not able to parse env properites, exiting.")

    def get(self, key):
        """get values"""
        return self.env_name_values[key]

    def has(self,key):
        """false if key not set or no value; otherwise true"""
        if key not in self.env_name_values or not self.env_name_values[key]:
            return False
        return True

    def set(self, key, value):
        """set values"""
        self.env_name_values[key] = value

    def setdefault(self, key, default_value):
        """if key does not exist nor has previous value set"""
        if key not in self.env_name_values or not self.env_name_values[key]:
            self.env_name_values[key] = default_value

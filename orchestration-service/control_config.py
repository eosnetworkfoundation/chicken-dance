"""Object holding and validating control UI configuration parameters"""
import os
import json
import requests

class ControlConfig():
    """obj holding and validating control UI params"""

    @staticmethod
    def config_files(root_dir):
        """get list of valid config files"""
        config_files = []
        for file_name in os.listdir(root_dir):
            if file_name.endswith('.json') and "test-" not in file_name:
                config_files.append(f'{root_dir}/{file_name}')
        return json.dumps(config_files)

    @staticmethod
    def set_version(new_version, config_file_path):
        """update spring version in config file"""
        # Load JSON data from file
        with open(config_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # Update 'leap_version' field in each record
        for record in data:
            record['leap_version'] = new_version

        # Save the updated data back to the file
        with open(config_file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)

    @staticmethod
    def get_versions(owner="antelopeIO", repo="spring"):
        """list versions for project"""
        # GitHub API endpoint for releases
        url = f"https://api.github.com/repos/{owner}/{repo}/releases"

        # Fetch the releases
        response = requests.get(url, timeout=3)
        releases = response.json()

        # Extract version tags, returns json array
        return json.dumps([release['tag_name'] for release in releases if 'tag_name' in release])

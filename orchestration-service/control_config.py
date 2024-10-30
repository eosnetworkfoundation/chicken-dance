"""Object holding and validating control UI configuration parameters"""
import os
import json
import re
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
        return config_files

    @staticmethod
    def set_version(new_version, config_file_path):
        """update spring version in config file"""

        if new_version.strip().lower() == "nochange":
            return
        # Load JSON data from file
        with open(config_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # Update 'spring_version' field in each record
        for record in data:
            record['spring_version'] = new_version

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
        return [release['tag_name'] for release in releases if 'tag_name' in release]

    @staticmethod
    def get_branches(owner="antelopeIO", repo="spring", token=None):
        """list all branches in a project"""
        # GitHub API endpoint for branches get first 100
        url = f"https://api.github.com/repos/{owner}/{repo}/branches?per_page=100&page=1"

        api_headers = {
            'Accept': 'application/vnd.github.v3+json',
            'X-GitHub-Api-Version': '2022-11-28'
         }

        # Add authorization if a token is provided
        if token:
            api_headers["Authorization"] = f'Bearer {token}'

        # Fetch the branches
        response = requests.get(url, headers=api_headers, timeout=3)

        # Parse the branch names from the JSON response
        branches = response.json()
        # filter out just names
        branch_names = [branch["name"] for branch in branches]

        # Use regex to filter branches matching 'release/[1-9].[0-9]'
        release_pattern = re.compile(r"^release/[1-9]\.[0-9]+$")
        release_branches = [name for name in branch_names if release_pattern.match(name)]
        other_branches = [name for name in branch_names if not release_pattern.match(name)]

        # Sort release branches and other branches separately
        sorted_release_branches = sorted(release_branches, reverse=False)
        sorted_other_branches = sorted(other_branches, reverse=True)

        # Combine lists with release branches at the front
        sorted_branch_names = sorted_release_branches + sorted_other_branches
        return sorted_branch_names

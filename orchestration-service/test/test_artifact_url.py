"""Module provides testing."""
import os
import pytest
import time
from get_artifact_url import ArtifactURL
from control_config import ControlConfig


def get_token():
    """get the token for github API"""
    file_path = os.path.expandvars("$HOME/env")

    # Open and read the file
    with open(file_path, "r") as file:
        for line in file:
            if line.startswith("BEARER_TOKEN="):
                # Strip off "BEARER_TOKEN=" and any surrounding whitespace
                return line.split("BEARER_TOKEN=", 1)[1].strip()

    return None

def test_all_branches():
    [org,repo,artifact_name] = ["AntelopeIO","spring","antelope-spring-deb-amd64"]
    token = get_token()
    branches = ControlConfig.get_branches(org,repo)
    for branch in branches:
        #if branch in ["tmp_sys_tests_debug","threshold_fix","test-slow-ship","test-kill","test-appbase"]:
        #    continue
        artifact_dict_response = ArtifactURL.deb_url_by_branch(
            org,
            repo,
            branch,
            artifact_name,
            token)
        if not artifact_dict_response or artifact_dict_response['success'] != True:
            print (f"{branch} *** Error {artifact_dict_response['errormsg']}")
        else:
            print (f"{branch} --- Succ  ")

        time.sleep(2)
        #assert artifact_dict_response is not None
        #assert artifact_dict_response['success'] == True
if __name__ == '__main__':
    test_all_branches()

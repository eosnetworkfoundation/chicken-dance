"""Calculated the url to download CI/CD build from github"""
from datetime import datetime
import json
import requests

class ArtifactURL():
    """Return download URL for artifact given an org, repo, and branch"""

    @staticmethod
    def deb_url_by_branch(org, repo, branch, artifact, token):
        """Return download URL for artifact given an org, repo, and branch"""

        #note spring artifact is antelope-spring-deb-amd64
        data = {
            'errorcode': None,
            'errormsg': None,
            'success': False,
            'url': None
        }

        if not token:
            data['errorcode'] = 405
            data['errormsg'] = "no token provided, not authorized"
            return data
        if not (org and repo and branch and artifact):
            data['errorcode'] = 404
            data['errormsg'] = "must provide org, repo, branch, and artifact"
            return data

        merge_sha = ArtifactURL.get_most_recent_merge_sha(org, repo, branch, token)
        if not merge_sha:
            data['errorcode'] = 400
            data['errormsg'] = "error fetching merge sha"
            return data

        build_action_id = ArtifactURL.get_latest_build_action(org, repo, 'Build & Test', merge_sha, token)
        if not build_action_id:
            data['errorcode'] = 400
            data['errormsg'] = "error fetching build action"
            return data

        url = ArtifactURL.get_deb_download_url(org, repo, artifact, build_action_id, token)
        if not url:
            data['errorcode'] = 400
            data['errormsg'] = "error fetching download URL"
            return data

        data['url'] = url
        data['success'] = True
        return data

    @staticmethod
    def api_headers(token):
        """Headers always the same"""
        return {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'Authorization': "Bearer "+token
        }

    @staticmethod
    def get_most_recent_merge_sha(org, repo, branch, token):
        """get latest merge SHA"""
        url = f"https://api.github.com/repos/{org}/{repo}/pulls?state=all&base=main&per_page=100&page=1"
        # Fetch the pull requests
        git_hub_pulls_response = requests.get(url,
            headers=ArtifactURL.api_headers(token),
            timeout=5)

        if git_hub_pulls_response.status_code != 200:
            return None

        root_json = git_hub_pulls_response.content.decode('utf-8')
        pull_requests = json.loads(root_json)
        if len(pull_requests) <= 0:
            return None

        for pr_item in pull_requests:
            if pr_item['head']['ref'] == branch:
                return pr_item['merge_commit_sha']

        return None

    @staticmethod
    def get_latest_build_action(org, repo, action, merge_sha, token):
        """Search through workflow
        by looking head sha for all pull requests
        look for the most recent action"""

        # this will store the record for the most recent action
        latest_action = {}
        # set url
        url=f'https://api.github.com/repos/{org}/{repo}/actions/runs'
        # set params
        params = {'merge_sha': merge_sha, 'event': 'pull_request'}

        # API Request
        query_runs = requests.get(url,
            params=params,
            headers=ArtifactURL.api_headers(token),
            timeout=10)

        if query_runs.status_code != 200:
            return None

        root_json = query_runs.content.decode('utf-8')
        root = json.loads(root_json)


        for record in root['workflow_runs']:
            workflow_id = record['id']
            workflow_name = record['name']
            update_time = datetime.strptime(record['updated_at'], '%Y-%m-%dT%H:%M:%SZ')

            # match our action
            if workflow_name == action:
                # update with latest where name equals action param
                if not latest_action or \
                    latest_action['update_time'] < update_time:
                    latest_action = {
                        'update_time': update_time,
                        'name': workflow_name,
                        'id': workflow_id,
                        'sha': record['head_sha'],
                        'status': record['status']
                    }

        if not latest_action or 'id' not in latest_action:
            return None
        return latest_action['id']

    @staticmethod
    def get_deb_download_url(org, repo, artifact_name, artifact_id, token):
        """get the url for the deb from the build action"""
        url=f"https://api.github.com/repos/{org}/{repo}/actions/runs/{artifact_id}/artifacts"

        # API Request
        query_artifacts = requests.get(url,
            headers=ArtifactURL.api_headers(token),
            timeout=10)

        if query_artifacts.status_code != 200:
            return None

        root_json = query_artifacts.content.decode('utf-8')
        root = json.loads(root_json)

        for item in root['artifacts']:
            # print (f"ARTIFACT ----> {item['name']} COMPARING --> {artifact_name}")
            if item['name'] == artifact_name and not item['expired']:
                # print (f"matching artifact {item['name']} with id {item['id']}")
                return  item['archive_download_url']
        return None

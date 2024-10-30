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

        # search latest in our branch true for release branches
        # if no matches on base branch open search up to all
        url = f"https://api.github.com/repos/{org}/{repo}/branches/{branch}"
        # Fetch the branch info
        git_branch_response = requests.get(url,
            headers=ArtifactURL.api_headers(token),
            timeout=5)

        if git_branch_response.status_code != 200:
            return None

        root_json = git_branch_response.content.decode('utf-8')
        branch_info = json.loads(root_json)
        # no matches don't paginate skip widen search
        if len(branch_info) <= 0:
            return None

        if 'commit' in branch_info and 'sha' in branch_info['commit']:
            return branch_info['commit']['sha']

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

        params = {'head_sha': merge_sha}
        #print (f"searching actions with {params}")

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
            if workflow_name == action \
                and record['status'] == 'completed' and record['conclusion'] == 'success':
                # update with latest where name equals action param
                if not latest_action or latest_action['update_time'] < update_time:
                    latest_action = {
                        'update_time': update_time,
                        'name': workflow_name,
                        'id': workflow_id,
                        'sha': record['head_sha'],
                        'head_branch': record['head_branch']
                    }
                    if 'pull_requests' in record and len(record['pull_requests']) > 0:
                        latest_action['pull_requests'] = record['pull_requests'][0]['url']

        if latest_action and 'id' in latest_action:
            # print(f'associated action {latest_action}')
            return latest_action['id']

        return None

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

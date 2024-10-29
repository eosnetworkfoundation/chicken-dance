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
        latest_pr = {}

        # search latest in our branch true for release branches
        # if no matches on base branch open search up to all
        for search_branch in [branch, 'all']:
            # loop through 8 pages each page with 80 items (8x80=640)
            # only PRs for our branch
            # print(f'********* Start Search **** {search_branch}')
            for page_num in range(1, 9):
                url = f"https://api.github.com/repos/{org}/{repo}/pulls?state=all&per_page=80&page={page_num}"
                # add base branch filter
                if search_branch != 'all':
                    url = url + f"&base={search_branch}"
                # Fetch the pull requests
                git_hub_pulls_response = requests.get(url,
                    headers=ArtifactURL.api_headers(token),
                    timeout=5)

                if git_hub_pulls_response.status_code != 200:
                    continue

                root_json = git_hub_pulls_response.content.decode('utf-8')
                pull_requests = json.loads(root_json)
                # no matches don't paginate skip widen search
                if len(pull_requests) <= 0:
                    break


                # Skip the following PRs
                #   closed PRs with no merged_at time, they are canceled
                #   open PRs with no created_at time, they shouldn't exist
                for pr_item in pull_requests:
                    # skip broad searches where head branch isn't ours
                    if search_branch == 'all':
                        if 'head' not in pr_item or 'ref' not in pr_item['head'] \
                          or pr_item['head']['ref'] != branch:
                            continue
                    if not (pr_item['state'] == 'closed' and not pr_item['merged_at']) \
                        and not (pr_item['state'] == 'open' and not pr_item['created_at']):
                        # for clarity calc the state dependant last update datetime
                        last_updated = None
                        if pr_item['state'] == 'open':
                            last_updated = datetime.strptime(pr_item['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                        if pr_item['state'] == 'closed':
                            last_updated = datetime.strptime(pr_item['merged_at'], '%Y-%m-%dT%H:%M:%SZ')

                        # initialize latest PR or update with new commit_sha and new update datetime
                        if pr_item['state'] in latest_pr and latest_pr[pr_item['state']]:
                            if last_updated and latest_pr[pr_item['state']]['updated'] < last_updated:
                                if 'head' in pr_item and 'sha' in pr_item['head']:
                                    latest_pr[pr_item['state']] = {
                                        'updated': last_updated,
                                        'commit_sha': pr_item['head']['sha'],
                                        'pr_url': pr_item['html_url']
                                    }
                                    #print(f"search for merge {latest_pr}")
                        else:
                            if 'head' in pr_item and 'sha' in pr_item['head']:
                                latest_pr[pr_item['state']] = {
                                    'updated': last_updated,
                                    'commit_sha': pr_item['head']['sha'],
                                    'pr_url': pr_item['html_url']
                                }
                                #print(f"search for merge {latest_pr}")

            # prefer closed PR with most recently 'merged_at'
            # otherwise take open PR with most recently updates 'updated_at'
            if 'closed' in latest_pr and latest_pr['open']:
                return latest_pr['closed']['commit_sha']
            if 'open' in latest_pr and latest_pr['open']:
                return latest_pr['open']['commit_sha']

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
        # check 'head_sha' first, then check merge into other branches 'merge_sha'
        for property in ['head_sha']:

            params = {property: merge_sha, 'event': 'pull_request'}
            #print (f"searching actions with {params}")

            # API Request
            query_runs = requests.get(url,
                params=params,
                headers=ArtifactURL.api_headers(token),
                timeout=10)

            if query_runs.status_code != 200:
                continue

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

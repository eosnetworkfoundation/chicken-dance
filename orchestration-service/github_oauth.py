"""modules to support oauth functions"""
import json
import requests

class GitHubOauth():
    """helper functions to manage git hub oauth"""

    @staticmethod
    def assemble_oauth_url(state, properties):
        """assemble url for initial oauth request"""
        return properties.get('authorize_url') \
            + f"?client_id={properties.get('client_id')}" \
            + f"&redirect_uri={properties.get('registered_callback')}" \
            + f"&scope={properties.get('scope')}" \
            + f"&state={state}" \
            + f"&allow_signup=false"

    @staticmethod
    def get_oauth_access_token(code, properties):
        """build url for the get token request"""
        # construct http call to exchange tempory code for access token
        params = {
            'client_id': properties.get('client_id'),
            'client_secret': properties.get('client_secret'),
            'code': code,
            'redirect_uri': properties.get('registered_callback')
        }
        # make post call to do exchange
        exchange_response = requests.post(properties.get('access_token'),
            params=params,
            timeout=3,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
        # if good get the token otherwise fail
        # returns following params access_token, scope, token_type
        if exchange_response.status_code == 200:
            exchange_data = json.loads(exchange_response.content.decode('utf-8'))
            return exchange_data['access_token']
        return None

    @staticmethod
    def create_auth_string(bearer_token, user_info_url):
        """get public profile information using token"""
        # https request to get public profile data, login and avatar_url
        user_avatar_response = requests.get(user_info_url,
            timeout=3,
            headers={
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {bearer_token}',
                'X-GitHub-Api-Version': '2022-11-28'
            })
        if user_avatar_response.status_code == 200:
            user_data = json.loads(user_avatar_response.content.decode('utf-8'))
            return GitHubOauth.credentials_to_str(user_data['login'],user_data['avatar_url'],bearer_token)
        return None

    @staticmethod
    def check_membership(bearer_token, login, team_string):
        """Check for team membership"""
        if not login:
            return False
        org, team = team_string.split('/',1)
        url = f'https://api.github.com/orgs/{org}/teams/{team}/members'
        membership_check = requests.get(url,
            timeout=3,
            headers={
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {bearer_token}',
                'X-GitHub-Api-Version': '2022-11-28',
                'User-Agent': 'App/OAuth/ReplayTest'
            })
        if membership_check.status_code == 200:
            members_list = json.loads(membership_check.content.decode('utf-8'))
            for member in members_list:
                if member['login'] == login:
                    return True
        return False

    @staticmethod
    def is_authorized(cookies, header_token, user_info_url, team_string):
        """check for authorized token or cookie"""

        token = None
        if 'replay_auth' in cookies and cookies['replay_auth']:
            token = GitHubOauth.extract_token(cookies['replay_auth'])
        if header_token:
            token = header_token
        if not token:
            return False

        auth_string = GitHubOauth.create_auth_string(token, user_info_url)
        login = GitHubOauth.extract_login(auth_string)
        return GitHubOauth.check_membership(token, login, team_string)

    @staticmethod
    def credentials_to_str(login, avatar_url, token):
        """converts profile data to string sep by :"""
        return token + ":" + login + ":" + avatar_url

    @staticmethod
    def str_to_public_profile(data):
        """converts str to array of profile data"""
        if not data:
            return []
        # return public profile data leaving off bearer token
        return data.split(':', 2)[1:]

    @staticmethod
    def extract_token(data):
        """grabs the bearer token from string"""
        if not data:
            return []
        return data.split(':', 2)[0]

    @staticmethod
    def extract_login(data):
        """grabs the bearer token from string"""
        if not data:
            return []
        return data.split(':', 2)[1]

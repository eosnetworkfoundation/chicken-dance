"""modules to support oauth functions"""
import json
import random
import requests

class GitHubOauth():
    """helper functions to manage git hub oauth"""
    def __init__(self,properties):
        self.client_id=properties.get('client_id')
        self.scope=properties.get('scope')
        self.client_secret=properties.get('client_secret')
        self.authorize_url=properties.get('authorize_url')
        self.registered_callback=properties.get('registered_callback')
        self.access_endpoint=properties.get('access_token')
        self.user_info_url=properties.get('user_info_url')
        self.login = None
        self.avatar_url = None
        self.state = None
        self.bearer_token = None
        self.words=['Also', 'Able',  'Acid',  'Aged',  'Away',  'Baby',  'Back',  'Bank',  'Been', \
            'Ball',  'Base',  'Busy',  'Bend',  'Bell',  'Bird',  'Cake',  'Peer',  'Real',  'Come', \
            'Came',  'Calm',  'Card',  'Coat',  'City',  'Chat',  'Cash',  'Crow',  'Cook',  'Cool', \
            'Dark',  'Each',  'Evil',  'Even',  'Ever',  'Face',  'Fact',  'Four',  'Five',  'Fair', \
            'Feel',  'Fell',  'Fire',  'Fine',  'Fish',  'Game',  'Gone',  'Gold',  'Girl',  'Have', \
            'Hair',  'Here',  'Hear',  'Into',  'Iron',  'Jump',  'Kick',  'Kill',  'Life',  'Like', \
            'Love',  'Main',  'Move',  'Meet',  'More',  'Nose',  'Near',  'Open',  'Only',  'Push', \
            'Pull',  'Sell',  'Sale']

    def assemble_state(self, count=3):
        """build up a state out of 3 random words from static dic"""
        selected_words = random.sample(self.words, count)
        # Join the selected words into a single string
        return ''.join(selected_words)

    def valid_state(self, state):
        """check state matches what we build"""
        if not state or state != self.state:
            return False
        return True

    def assemble_oauth_url(self):
        """assemble url for initial oauth request"""
        # build new state by randomly selecting 3 words
        self.state = self.assemble_state()
        return self.authorize_url \
            + f"?client_id={self.client_id}" \
            + f"&redirect_uri={self.registered_callback}" \
            + f"&scope={self.scope}" \
            + f"&state={self.state}" \
            + f"&allow_signup=false"

    def get_access_token(self, code):
        """build url for the get token request"""
        # construct http call to exchange tempory code for access token
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.registered_callback
        }
        # make post call to do exchange
        exchange_response = requests.post(self.access_endpoint,
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
            self.bearer_token = exchange_data['access_token']
            return True
        return False

    def get_public_profile(self):
        """get public profile information using token"""
        # https request to get public profile data, login and avatar_url
        user_avatar_response = requests.get(self.user_info_url,
            timeout=3,
            headers={
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {self.bearer_token}',
                'X-GitHub-Api-Version': '2022-11-28'
            })
        if user_avatar_response.status_code == 200:
            user_data = json.loads(user_avatar_response.content.decode('utf-8'))
            self.login = user_data['login']
            self.avatar_url = user_data['avatar_url']
            return True
        return False

    def profile_to_str(self):
        """converts profile data to string sep by :"""
        return self.login + ":" + self.avatar_url

    def str_to_profile(self, data):
        """converts str to array of profile data"""
        return data.split(':', 1)

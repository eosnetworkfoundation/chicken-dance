"""Module tests web API expecting 403 auth failure"""
import requests
import pytest
import re
import json

@pytest.fixture(scope="module")
def setup_module():
    """setting some constants to avoid mis-spellings"""
    setup = {}
    setup['base_url']='http://127.0.0.1:4000'

    setup['plain_text_headers'] = {
        'Accept': 'text/plain; charset=utf-8',
        'Content-Type': 'text/plain; charset=utf-8',
    }

    setup['json_headers'] = {
        'Accept': 'application/json',
        'Content-Type': 'application/json; charset=utf-8',
    }

    setup['html_headers'] = {
        'Accept': 'text/html, application/xhtml+xml',
        'Content-Type': 'text/html; charset=utf-8',
    }

    return setup

def test_api_calls(setup_module):
    """Run through all API calls and make sure they fail with 403"""
    cntx = setup_module

    params = { 'nextjob': 1, 'sliceid': 3 }
    api_calls = ['/job', '/status', '/config', '/summary', '/progress', '/grid', '/control', '/detail', '/logout']
    for path in api_calls:
        response = requests.get(cntx['base_url'] + '/job',
            params=params,
            timeout=3,
            headers=cntx['json_headers'])
        assert response.status_code == 403

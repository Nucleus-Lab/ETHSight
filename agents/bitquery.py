import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import os

class BitqueryAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://graphql.bitquery.io"
        self.headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key
        }

    def _make_request(self, query):
        """
        Make a request to Bitquery API
        """
        try:
            response = requests.post(
                self.base_url,
                json={"query": query},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            return None
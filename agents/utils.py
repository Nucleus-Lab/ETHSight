import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import os

class BitqueryAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://streaming.bitquery.io/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def request(self, query: str, variables: dict = None):
        """
        Make a request to Bitquery API
        
        Args:
            query (str): GraphQL query string
            variables (dict, optional): Variables for the query. Defaults to None.
            
        Returns:
            dict: Response data or None if error
        """
        try:
            payload = {
                "query": query,
                "variables": variables or {}
            }
            
            response = requests.post(
                self.base_url,
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            return None
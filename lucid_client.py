from argparse import Namespace
from typing import Dict, Any
import file_utils
import jira_client
import lucid_client
import os
import requests

def create_lucid_board(args: Namespace) -> Dict[str, Any]:
  email = input("Enter the email of your Jira user: ")
  year = int(input("Enter the year you want the Jira history for: "))
  product = input("What Lucid product would you like to import this document into? (lucidchart/lucidspark): ")
  
  issues = jira_client.get_jira_issues(email, year)
  issues_by_quarter = jira_client.sort_issues_by_quarter(issues, year, email, args)
  file_utils.generate_json_file(issues_by_quarter)
  file_utils.create_zip_file()
  return lucid_client.send_lucid_import_request(email, year, product)

def send_lucid_import_request(email: str, year: int, product: str) -> Dict[str, Any]:
  print("Sending request to create Lucid document...")
  url = "https://api.lucid.co/documents"
 
  headers = {
    "Authorization": f'Bearer {os.getenv("LUCID_OAUTH2_TOKEN")}',
    "Lucid-Api-Version": f"{1}"
  }

  files = {
    "file": ('standard.lucid', open('standard.lucid', 'rb'), 'x-application/vnd.lucid.standardImport')
  }
  
  data = {
    "title": f"{email.split('@')[0]} Jira History - {year}",
    "product": product
  }
  
  response = requests.post(url = url, headers = headers, data = data, files = files)
  file_utils.cleanup()
  response.raise_for_status()
  return response.json()

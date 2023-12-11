from datetime import datetime
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
import argparse
import csv
import json
import os
import requests
import zipfile
 
def create_lucid_board(args):
  email = input("Enter the email of your Jira user: ")
  year = int(input("Enter the year you want the Jira history for: "))
  product = input("What Lucid product would you like to import this document into? (lucidchart/lucidspark): ")
  
  issues = get_jira_issues(email, year, args)
  generate_json_file(issues)
  create_zip_file()
  return send_lucid_import_request(email, year, product)
  
def get_jira_issues(email, year, args):
  print("Fetching issues from Jira...")
  url = f"https://{os.getenv('JIRA_SUBDOMAIN')}.atlassian.net/rest/api/3/search"
 
  auth = HTTPBasicAuth(os.getenv("JIRA_AUTH_EMAIL"), os.getenv("JIRA_API_KEY"))
 
  headers = {
    "Accept": "application/json"
  }
  
  issues = []
  
  start = 0
  max_results = 50
  total_returned = max_results
  total = -1
  
  while total_returned == max_results and start != total:
  
    query = {
      "jql": f"""assignee = '{email}' 
        AND created >= '{year}-01-01'
        AND created <= '{year}-12-31'
        AND status = Closed""",
      "startAt": f"{start}",
      "maxResults": f"{max_results}"
    }
  
    response = requests.request(
        "GET",
        url,
        headers=headers,
        params=query,
        auth=auth
    )
    response.raise_for_status()
  
    data = json.loads(response.text)
    
    total = data['total']
    total_returned = len(data['issues'])
    start += total_returned
    
    issues += data['issues']
    
    print(f"{start} of {total} issues received from Jira")
  

  # sort based on earliest to latest completed
  issues.sort(key = get_updated_or_created_date)
  
  issues_by_quarter = {
  'Q1': [],
  'Q2': [],
  'Q3': [],
  'Q4': []
  }
  
  # Get issues and put them into appropriate Quarter array
  for issue in issues:
    # Assign quarter based on when the issue status was changed to "closed"
    closed_date = get_updated_or_created_date(issue)
    closed_minus_timezone = closed_date[:-5]
    parsed_datetime = datetime.strptime(closed_minus_timezone, '%Y-%m-%dT%H:%M:%S.%f')
    
    if datetime(year, 1, 1) <= parsed_datetime <= datetime(year, 3, 31):
      issues_by_quarter['Q1'].append(issue)
    elif datetime(year, 4, 1) <= parsed_datetime <= datetime(year, 6, 30):
      issues_by_quarter['Q2'].append(issue)
    elif datetime(year, 7, 1) <= parsed_datetime <= datetime(year, 9, 30):
      issues_by_quarter['Q3'].append(issue)
    else:
      issues_by_quarter['Q4'].append(issue)
    
  if args.debug:
    save_parsed_issues_to_csv(issues_by_quarter, year, email)
    save_raw_issues_to_json(issues, year, email)
  
  return issues_by_quarter

def get_updated_or_created_date(issue):
  return_var = "1970-01-01T12:00:00.000-0700"
  
  if 'fields' in issue:
    if 'statuscategorychangedate' in issue['fields'] and issue['fields']['statuscategorychangedate'] is not None:
      return_var = issue['fields']['statuscategorychangedate']
    elif 'created' in issue['fields'] and issue['fields']['created'] is not None:
      return_var = issue['fields']['created']

  return return_var

def save_raw_issues_to_json(issues, year, email):
  with open(f"raw_issues_{email.split('@')[0]}_{year}.json", "w") as json_file:
    # Convert the dictionary to a JSON string
    json.dump(issues, json_file, indent=2)  # `indent` for pretty formatting


def save_parsed_issues_to_csv(issues, year, email):
  with open(f"jira_history_{email.split('@')[0]}_{year}.csv", "w", newline="") as csvfile:
    fieldnames = ['quarter', 'key', 'summary']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    for key, value in issues.items():
      for issue in value:
        simpIssue = {
          'quarter': f'{key}',
          'key': f'{issue["key"]}',
          'summary': f'{issue["fields"]["summary"]}'
        }
        writer.writerow(simpIssue)
    
def generate_json_file(issues):
  data = {
    "version": 1,
    "collections": [],
    "pages": [
      {
        "id": "page1",
        "title": "Main Plan",
        "shapes": []
      }
    ]
  }
  
  swimlane = {
    "id": "swimlane1",
    "type": "swimLanes",
    "boundingBox": {
      "x": 0,
      "y": 0,
      "w": 1280,
      "h": 1200 # This will get replaced with the max lane height later
    },
    "style": {
        "fill": {
        "type": "color",
        "color": "#ADD8E6"
      },
        "stroke": {
        "color": "#000000",
        "width": 2,
        "style": "solid"
      }
    },
    "magnetize": True,
    "vertical": True,
    "titleBar": {
      "height": 10,
      "verticalText": False
    },
    "lanes": [
      {
        "title": "Q1",
        "width": 320,
        "headerFill": "#ffffff",
        "laneFill": "#D3D3D3"
      },
      {
        "title": "Q2",
        "width": 320,
        "headerFill": "#ffffff",
        "laneFill": "#D3D3D3"
      },
      {
        "title": "Q3",
        "width": 320,
        "headerFill": "#ffffff",
        "laneFill": "#D3D3D3"
      },
      {
        "title": "Q4",
        "width": 320,
        "headerFill": "#ffffff",
        "laneFill": "#D3D3D3"
      }
    ]
  }

  data["pages"][0]["shapes"].append(swimlane)
  
  i = 0
  max_y = 0
  
  for key, value in issues.items():
    start_x = i * 320
    j = 0
    
    for issue in value:
      x = start_x + ((j % 3) * 105) + 5
      y = 50 + (j // 3) * 105
      
      if y > max_y:
        max_y = y
      
      shape = {
        "id": f"{issue['key']}",
        "type": "rectangle",
        "boundingBox": {
          "x": x,
          "y": y,
          "w": 100,
          "h": 100
        },
        "style": {
          "fill": {
            "type": "color",
            "color": "#ADD8E6"
          },
          "stroke": {
            "color": "#000000",
            "width": 1,
            "style": "solid"
          }
        },
        "text": f"<a href='https://{os.getenv('JIRA_SUBDOMAIN')}.atlassian.net/browse/{issue['key']}'>{issue['key']}</a>: {issue['fields']['summary']}",
      }
      
      data["pages"][0]["shapes"].append(shape)
      j += 1
    i += 1
  
  data["pages"][0]["shapes"][0]["boundingBox"]["h"] = max_y + 100 # the extra 100 pixels allows room for the title bar and bottom padding
  
  with open('document.json', 'w') as json_file:
    # Convert the dictionary to a JSON string
    json.dump(data, json_file, indent=2)  # `indent` for pretty formatting
  
def create_zip_file():
  with zipfile.ZipFile('standard.zip', 'w') as my_zip:
    # Add files to the zip (replace this with actual file paths)
    my_zip.write('document.json')

  # Rename the zip file to have a .lucid extension
  os.rename('standard.zip', 'standard.lucid')
  
def send_lucid_import_request(email, year, product):
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
  cleanup()
  response.raise_for_status()
  return response.json()
  
def cleanup():
    os.remove("document.json")
    os.remove("standard.lucid")
    
def parse_args():
  parser = argparse.ArgumentParser(description='''This Python script allows you to retrieve issues from Jira associated with a specific user 
                                   and organizes them into a Lucidchart document based on quarterly categorization.''')

  parser.add_argument(
    '-d', '--debug',
    action='store_true',
    help='''When this flag is set, two files will be created to assist in debugging. One will be a .csv file of the issues
            sorted by quarter, and the other will be a raw dump of all the JSON issues received from Jira.'''
)

  # Parse the arguments
  return parser.parse_args()
    
load_dotenv()

args = parse_args()
response_json = create_lucid_board(args)
print(f"Access the new document at: {response_json['editUrl']}")
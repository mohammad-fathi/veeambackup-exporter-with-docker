import time
import requests
from prometheus_client import start_http_server, Gauge
from urllib3.exceptions import InsecureRequestWarning
import os

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# CONFIGURATION SECTION
veeamRestServer = os.getenv("VEEAM_REST_SERVER")
veeamRestPort = os.getenv("VEEAM_REST_PORT")
veeamUsername = os.getenv("VEEAM_USERNAME")
veeamPassword = os.getenv("VEEAM_PASSWORD")

token_url = f'https://{veeamRestServer}:{veeamRestPort}/api/oauth2/token'
token_headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'x-api-version': '1.1-rev0'
}
token_data = {
    'grant_type': 'password',
    'username': veeamUsername,
    'password': veeamPassword,
    'refresh_token': 'string',
    'code': 'string',
    'use_short_term_refresh': 'true',
    'vbr_token': 'string'
}

def get_access_token(url, headers, data):
    try:
        response_token = requests.post(url, headers=headers, data=data, verify=False)
        response_token.raise_for_status()  # Raise an exception for HTTP errors
        return response_token.json().get('access_token')
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve access token: {e}")
        exit()

def get_job_statuses(url, headers):
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve job statuses: {e}")
        exit()

def update_metrics(jobs, job_status_gauge):
    if 'data' in jobs:
        for job in jobs['data']:
            name = job.get('name', 'Unknown')
            last_result = job.get('lastResult', 'Unknown')
            if last_result == 'Success':
                job_status_gauge.labels(job_name=name).set(1)
            elif last_result == 'Failed':
                job_status_gauge.labels(job_name=name).set(0)
            elif last_result == 'Warning':
                job_status_gauge.labels(job_name=name).set(2)
            else:
                job_status_gauge.labels(job_name=name).set(-1)  # Handle unexpected statuses
    else:
        print("No job data found")

if __name__ == '__main__':
    access_token = get_access_token(token_url, token_headers, token_data)
    
    # Update the jobs_headers with the new access token
    jobs_headers = {
        'Authorization': f'Bearer {access_token}',
        'x-api-version': '1.1-rev0'
    }
    
    # Define the jobs_url here
    jobs_url = f'https://{veeamRestServer}:{veeamRestPort}/api/v1/jobs/states'
    
    # Start the Prometheus metrics server
    start_http_server(8000)

    # Create a Prometheus gauge for job status
    job_status_gauge = Gauge('veeam_job_status', 'Status of Veeam jobs', ['job_name'])

    while True:
        job_statuses = get_job_statuses(jobs_url, jobs_headers)
        update_metrics(job_statuses, job_status_gauge)
        time.sleep(60)  # Update every minute

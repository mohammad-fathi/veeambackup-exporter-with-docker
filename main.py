import time
import requests
from prometheus_client import Gauge, generate_latest
from urllib3.exceptions import InsecureRequestWarning
from flask import Flask, Response
import os

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Flask app setup
app = Flask(__name__)

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

# Create a Prometheus gauge for job status
job_status_gauge = Gauge('veeam_job_status', 'Status of Veeam jobs', ['job_name'])

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

def update_metrics():
    jobs_url = f'https://{veeamRestServer}:{veeamRestPort}/api/v1/jobs/states'
    access_token = get_access_token(token_url, token_headers, token_data)

    # Update the jobs_headers with the new access token
    jobs_headers = {
        'Authorization': f'Bearer {access_token}',
        'x-api-version': '1.1-rev0'
    }

    job_statuses = get_job_statuses(jobs_url, jobs_headers)
    if 'data' in job_statuses:
        for job in job_statuses['data']:
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

@app.route('/metrics')
def metrics():
    update_metrics()  # Update metrics before exposing
    return Response(generate_latest(), mimetype='text/plain; charset=utf-8')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

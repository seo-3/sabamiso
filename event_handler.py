import boto3, os
import json
import requests
import logging
import time
from datetime import datetime, timezone, timedelta
from os import getenv

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

os.environ['TZ'] = 'Asia/Tokyo'
API_KEY = getenv("API_KEY")

code_pipeline = boto3.client('codepipeline')

def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }

def post_graph_annotations(api_key, payload, retry=5, wait=5):

    url = "https://mackerel.io/api/v0/graph-annotations"
    headers = {'Content-Type': 'application/json', 'X-Api-Key' : api_key}
    retry_count = 0
    response = None

    while True:
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)

        except Exception as e:
            logger.error(e)
        finally:
            if response is not None:
                if response.status_code == 200:
                    return True
            retry_count += 1
            if retry_count >= retry:
                return False
            time.sleep(wait)

def of(event, from_event, to_event):

    job_id = event['CodePipeline.job']['id']
    user_parameters = event['CodePipeline.job']['data']['actionConfiguration']['configuration']['UserParameters']
    decode_parameters = json.loads(user_parameters)

    return {
            'title':decode_parameters['title'],
            'description':job_id,
            'from':from_event,
            'to':to_event,
            'service':decode_parameters['service'],
            'roles':[decode_parameters['roles']],
    }

def lambda_handler(event, context):

    logger.info("Received event: %s", json.dumps(event, indent=2))
    payload = None

    try:
        job_id = event['CodePipeline.job']['id']
        now = time.time()
        JST = timezone(timedelta(hours=+9), 'JST')
        loc = datetime.fromtimestamp(now, JST)

        payload = of(event=event, from_event=loc.timestamp(), to_event=loc.timestamp())
        logger.info(payload)

        res = post_graph_annotations(
            api_key=API_KEY, payload=payload)

        if res == False:
            raise Exception
    except Exception as e:
        code_pipeline.put_job_failure_result(jobId=job_id)
        return respond(e)

    code_pipeline.put_job_success_result(jobId=job_id)
    return respond(None, payload)

if __name__ == "__main__":

	f = open("event.json", "r")

	event = json.load(f)
	context = ""
	f.close()

	lambda_handler(event, context)

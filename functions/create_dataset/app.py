"""
Create an Amazon Forecast dataset. The information about the dataset that you provide
helps AWS Forecast understand how to consume the data for model training.
"""
from os import environ
from datetime import datetime
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

DATASET_NAME = '{project_name}_{dataset_type}'
DATASET_ARN = 'arn:aws:forecast:{region}:{account}:dataset/{dataset_name}'

logger = Logger()
forecast_client = boto3.client('forecast')
account_id = boto3.client('sts').get_caller_identity()['Account']


def lambda_handler(event, _):
    """
    Lambda function handler
    """
    logger.info({'message': 'Event received', 'event': event})

    datasets = event['Datasets']
    event['AccountID'] = account_id
    event['CurrentDate'] = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    event['DatasetName'] = DATASET_NAME.format(
        project_name=event['ProjectName'],
        dataset_type=datasets[0]['DatasetType']
    )
    event['DatasetArn'] = DATASET_ARN.format(
        region=environ['AWS_REGION'],
        account=event['AccountID'],
        dataset_name=event['DatasetName']
    )
    try:
        response = forecast_client.describe_dataset(
            DatasetArn=event['DatasetArn']
        )
        logger.info({
            'message': 'forecast_client.describe_dataset called',
            'response': response
        })
    except forecast_client.exceptions.ResourceNotFoundException:
        logger.info('Dataset not found. Will follow to create dataset.')
        for dataset in datasets:
            response = forecast_client.create_dataset(
                **dataset,
                DatasetName=event['DatasetName']
            )
            logger.info({
                'message': 'Called forecast_client.create_dataset',
                'response': response
            })
        response = forecast_client.describe_dataset(
            DatasetArn=event['DatasetArn']
        )
        logger.info({
            'message': 'Called forecast_client.describe_dataset',
            'response': response
        })

    actions.take_action(response['Status'])
    return event

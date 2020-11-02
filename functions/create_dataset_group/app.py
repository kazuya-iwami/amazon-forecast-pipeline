"""
Create an Amazon Forecast dataset group which can contain one or multiple dataset(s).
"""
from os import environ
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

DATASET_GROUP_NAME = '{project_name}'
DATASET_GROUP_ARN = 'arn:aws:forecast:{region}:{account}:dataset-group/{dataset_group_name}'

logger = Logger()
forecast_client = boto3.client('forecast')


def lambda_handler(event, _):
    """
    Lambda function handler
    """
    logger.info({'message': 'Event received', 'event': event})

    event['DatasetGroupName'] = DATASET_GROUP_NAME.format(
        project_name=event['ProjectName']
    )
    event['DatasetGroupArn'] = DATASET_GROUP_ARN.format(
        region=environ['AWS_REGION'],
        account=event['AccountID'],
        dataset_group_name=event['DatasetGroupName'],
    )
    try:
        response = forecast_client.describe_dataset_group(
            DatasetGroupArn=event['DatasetGroupArn']
        )
        logger.info({
            'message': 'forecast_client.describe_dataset_group called',
            'response': response
        })

    except forecast_client.exceptions.ResourceNotFoundException:
        logger.info(
            'Dataset Group not found. Creating new dataset group.'
        )
        # TODO: Support multiple datasets
        response = forecast_client.create_dataset_group(
            **event['DatasetGroup'],
            DatasetGroupName=event['DatasetGroupName'],
            DatasetArns=[event['DatasetArn']]
        )
        logger.info({
            'message': 'forecast_client.create_dataset_group called',
            'response': response
        })

        response = forecast_client.describe_dataset_group(
            DatasetGroupArn=event['DatasetGroupArn']
        )
        logger.info({
            'message': 'forecast_client.describe_dataset called',
            'response': response
        })

    # When the resource is in CREATE_PENDING or CREATE_IN_PROGRESS,
    # ResourcePending exception will be thrown and this Lambda function will be retried.
    actions.take_action(response['Status'])
    return event

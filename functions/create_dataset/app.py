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
    current_date = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    logger.structure_logs(
        append=True, lambda_name='create_dataset', trace_id=current_date)
    logger.info({'message': 'Event received', 'event': event})

    # TODO: Support multiple datasets
    # Replace hyphen of stack_name to underscore because some resource names do not support hyphen.
    event['ProjectName'] = environ['STACK_NAME'].replace('-', '_')
    event['AccountID'] = account_id
    event['CurrentDate'] = current_date
    event['DatasetName'] = DATASET_NAME.format(
        project_name=event['ProjectName'],
        dataset_type=event['Datasets'][0]['DatasetType']
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
        for dataset in event['Datasets']:
            logger.info({
                'message': 'creating new dataset',
                'dataset_arn': event['DatasetArn']
            })
            response = forecast_client.create_dataset(
                **dataset,
                DatasetName=event['DatasetName']
            )
            logger.info({
                'message': 'forecast_client.create_dataset called',
                'response': response
            })

        response = forecast_client.describe_dataset(
            DatasetArn=event['DatasetArn']
        )
        logger.info({
            'message': 'forecast_client.describe_dataset called',
            'response': response
        })

    # When the resource is in CREATE_PENDING or CREATE_IN_PROGRESS,
    # ResourcePending exception will be thrown and this Lambda function will be retried.
    actions.take_action(response['Status'])

    logger.info({
        'message': 'datasets were created successfully',
        'dataset_arns': [event['DatasetArn']]
    })
    return event

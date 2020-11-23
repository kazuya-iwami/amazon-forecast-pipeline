"""
Create an Amazon Forecast dataset. The information about the dataset that you provide
helps AWS Forecast understand how to consume the data for model training.
"""
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

DATASET_NAME = '{project_name}_{dataset_type}'
DATASET_ARN = 'arn:aws:forecast:{region}:{account}:dataset/{dataset_name}'

logger = Logger()
forecast_client = boto3.client('forecast')


@lambda_handler_logger(logger=logger, lambda_name='create_dataset')
def lambda_handler(event, _):
    """
    Lambda function handler
    """
    # TODO: Support multiple datasets
    event['DatasetName'] = DATASET_NAME.format(
        project_name=event['ProjectName'],
        dataset_type=event['Datasets'][0]['DatasetType']
    )
    event['DatasetArn'] = DATASET_ARN.format(
        region=event['Region'],
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
        'message': 'datasets were created',
        'dataset_arns': [event['DatasetArn']]
    })
    return event

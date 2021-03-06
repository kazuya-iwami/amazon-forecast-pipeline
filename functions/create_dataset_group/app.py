"""
Create an Amazon Forecast dataset group which can contain one or multiple dataset(s).
"""
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

DATASET_GROUP_NAME = '{project_name}_{date}'
DATASET_GROUP_ARN = 'arn:aws:forecast:{region}:{account}:dataset-group/{dataset_group_name}'

logger = Logger()
forecast_client = boto3.client('forecast')


@lambda_handler_logger(logger=logger, lambda_name='create_dataset_group')
def lambda_handler(event, _):
    """
    Lambda function handler
    """
    event['DatasetGroupName'] = DATASET_GROUP_NAME.format(
        project_name=event['ProjectName'],
        date=event['TriggeredAt']
    )
    event['DatasetGroupArn'] = DATASET_GROUP_ARN.format(
        region=event['Region'],
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
        logger.info({
            'message': 'creating new dataset group',
            'dataset_group_arn': event['DatasetGroupArn']
        })
        response = forecast_client.create_dataset_group(
            **event['DatasetGroup'],
            DatasetGroupName=event['DatasetGroupName'],
            DatasetArns=[dataset['DatasetArn']
                         for dataset in event['Datasets']]
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

    logger.info({
        'message': 'dataset group was created',
        'dataset_group_arn': event['DatasetGroupArn']
    })

    return event

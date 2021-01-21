"""
Create an Amazon Forecast dataset. This function is called in update model flow.
"""
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

DATASET_NAME = '{project_name}_{dataset_type}_{date}'
DATASET_ARN = 'arn:aws:forecast:{region}:{account}:dataset/{dataset_name}'

logger = Logger()
forecast_client = boto3.client('forecast')


@lambda_handler_logger(logger=logger, lambda_name='create_dataset')
def lambda_handler(event, _):
    """
    Lambda function handler
    """
    # Create datasets
    for dataset in event['Datasets']:
        dataset_name = DATASET_NAME.format(
            project_name=event['ProjectName'],
            dataset_type=dataset['DatasetType'],
            date=event['TriggeredAt']
        )

        dataset_arn = DATASET_ARN.format(
            region=event['Region'],
            account=event['AccountID'],
            dataset_name=dataset_name
        )

        try:
            response = forecast_client.describe_dataset(
                DatasetArn=dataset_arn
            )
            logger.info({
                'message': 'forecast_client.describe_dataset called',
                'response': response,
                'dataset_arn': dataset_arn
            })

        except forecast_client.exceptions.ResourceNotFoundException:
            logger.info({
                'message': 'creating new dataset',
                'dataset_arn': dataset_arn
            })
            response = forecast_client.create_dataset(
                **dataset,
                DatasetName=dataset_name
            )
            logger.info({
                'message': 'forecast_client.create_dataset called',
                'response': response,
                'dataset_arn': dataset_arn
            })

            dataset['DatasetName'] = dataset_name
            dataset['DatasetArn'] = dataset_arn

    # Check dataset status
    for dataset in event['Datasets']:
        response = forecast_client.describe_dataset(
            DatasetArn=dataset['DatasetArn']
        )
        logger.info({
            'message': 'forecast_client.describe_dataset called',
            'response': response,
            'dataset_arn': dataset_arn
        })

        # When the resource is in CREATE_PENDING or CREATE_IN_PROGRESS,
        # ResourcePending exception will be thrown and this Lambda function will be retried.
        actions.take_action(response['Status'])

    # All datasets were create
    logger.info({
        'message': 'all datasets were created',
        'dataset_arns': [dataset['DatasetArn'] for dataset in event['Datasets']]
    })
    return event

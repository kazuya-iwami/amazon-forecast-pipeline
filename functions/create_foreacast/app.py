"""
Creates a forecast for each item in the target_time_series dataset.
"""
from os import environ
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

FORECAST_NAME = '{project_name}_{date}'
FORECAST_ARN = 'arn:aws:forecast:{region}:{account}:forecast/{forecast_name}'

logger = Logger()
forecast_client = boto3.client('forecast')


def lambda_handler(event, _):
    """
    Lambda function handler
    """
    logger.info({'message': 'Event received', 'event': event})

    event['ForecastName'] = FORECAST_NAME.format(
        project_name=event['ProjectName'],
        date=event['CurrentDate']
    )
    event['ForecastArn'] = FORECAST_ARN.format(
        region=environ['AWS_REGION'],
        account=event['AccountID'],
        forecast_name=event['ForecastName']
    )

    try:
        response = forecast_client.describe_forecast(
            ForecastArn=event['ForecastArn']
        )
        logger.info({
            'message': 'forecast_client.describe_forecast called',
            'response': response
        })

    except forecast_client.exceptions.ResourceNotFoundException:
        logger.info('Forecast not found. Creating new forecast.')
        response = forecast_client.create_forecast(
            **event['Forecast'],
            ForecastName=event['ForecastName'],
            PredictorArn=event['PredictorArn']
        )
        logger.info({
            'message': 'forecast_client.create_forecast called',
            'response': response
        })

        response = forecast_client.describe_forecast(
            ForecastArn=event['ForecastArn']
        )
        logger.info({
            'message': 'forecast_client.describe_forecast called',
            'response': response
        })

    # When the resource is in CREATE_PENDING or CREATE_IN_PROGRESS,
    # ResourcePending exception will be thrown and this Lambda function will be retried.
    actions.take_action(response['Status'])
    return event

"""
Creates a forecast for each item in the target_time_series dataset.
"""
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

FORECAST_NAME = '{project_name}_{date}'
FORECAST_ARN = 'arn:aws:forecast:{region}:{account}:forecast/{forecast_name}'


logger = Logger()
forecast_client = boto3.client('forecast')


@lambda_handler_logger(logger=logger, lambda_name='create_foreacast')
def lambda_handler(event, _):
    """
    Lambda function handler
    """
    event['ForecastName'] = FORECAST_NAME.format(
        project_name=event['ProjectName'],
        date=event['TriggeredAt']
    )
    event['ForecastArn'] = FORECAST_ARN.format(
        region=event['Region'],
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
        latest_predictor_arn = event['LATEST_PREDICTOR_ARN']

        logger.info({
            'message': 'creating new forecast',
            'forecast_arn': event['ForecastArn'],
            'predictor_arn': latest_predictor_arn
        })
        response = forecast_client.create_forecast(
            **event['Forecast'],
            ForecastName=event['ForecastName'],
            PredictorArn=latest_predictor_arn
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

    logger.info({
        'message': 'forecast was created',
        'forecast_arn': event['ForecastArn']
    })

    return event

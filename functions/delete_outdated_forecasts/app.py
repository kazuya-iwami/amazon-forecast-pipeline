"""
Delete outdated forecasts
"""
import re
import datetime
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

PATTERN = r'^arn:aws:forecast:.+?:.+?:forecast\/(.+?)_([0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2})'

logger = Logger()
forecast_client = boto3.client('forecast')
compiled_pattern = re.compile(PATTERN)


def list_target_forecast_arns(project_name, current_date, status):
    """
    List forecast ARNs which should be deleted.
    """
    response = forecast_client.list_forecasts(
        Filters=[
            {
                'Key': 'Status',
                'Value': status,
                'Condition': 'IS'
            },
        ]
    )
    logger.info({
        'message': 'forecast_client.list_forecast_forecasts called',
        'response': response
    })
    forecast_arns = [forecast['ForecastArn']
                     for forecast in response['Forecasts']]
    target_forecast_arns = []

    for forecast_arn in forecast_arns:
        result = compiled_pattern.match(forecast_arn)
        if result:
            # Check if the forecast is associated to the target project.
            retrieved_project_name = result.group(1)
            if retrieved_project_name == project_name:
                target_forecast_arns.append(forecast_arn)

    logger.info({
        'message': 'list_target_forecast_arns() completed',
        'project_name': project_name,
        'current_date': current_date,
        'status': status,
        'result': target_forecast_arns
    })
    return target_forecast_arns


@lambda_handler_logger(logger=logger, lambda_name='delete_outdated_forecasts')
def lambda_handler(event, _):
    """
    Lambda function handler
    """
    target_forecast_arns = list_target_forecast_arns(
        event['ProjectName'], event['TriggeredAt'], 'ACTIVE')

    # Delete resources
    for forecast_arn in target_forecast_arns:
        try:
            response = forecast_client.delete_forecast(
                ForecastArn=forecast_arn
            )
            logger.info({
                'message': 'forecast_client.delete_forecast called',
                'response': response
            })
        except forecast_client.exceptions.ResourceNotFoundException:
            logger.warn({
                'message': 'Forecast has already been deleted',
                'forecast_arn': forecast_arn
            })

    # When the resource is in DELETE_PENDING or DELETE_IN_PROGRESS,
    # ResourcePending exception will be thrown and this Lambda function will be retried.
    deleting_forecast_arns = \
        list_target_forecast_arns(event['ProjectName'], event['TriggeredAt'], 'DELETE_PENDING') + \
        list_target_forecast_arns(
            event['ProjectName'], event['TriggeredAt'], 'DELETE_IN_PROGRESS')
    if len(deleting_forecast_arns) != 0:
        logger.info({
            'message': 'these resources are deleting.',
            'deleting_forecast_arns': deleting_forecast_arns
        })
        raise actions.ResourcePending

    return event

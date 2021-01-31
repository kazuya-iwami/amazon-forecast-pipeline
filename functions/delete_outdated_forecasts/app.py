"""
Delete outdated forecasts
"""
import re
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

PATTERN = r'^arn:aws:forecast:.+?:.+?:forecast\/(.+?)_([0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2})'

logger = Logger()
forecast_client = boto3.client('forecast')
compiled_pattern = re.compile(PATTERN)


def get_deletion_target_forecast_arns(project_name, status_list):
    """
    List forecast ARNs which should be deleted.
    """
    # Get all forecasts
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/forecast.html#ForecastService.Client.list_forecasts
    deletion_target_forecast_arns = []

    paginator = forecast_client.get_paginator('list_forecasts')
    filters = []
    status_candidate = ['ACTIVE', 'CREATE_PENDING', 'CREATE_IN_PROGRESS', 'CREATE_FAILED',
                        'DELETE_PENDING', 'DELETE_IN_PROGRESS', 'DELETE_FAILED',
                        'UPDATE_PENDING', 'UPDATE_IN_PROGRESS', 'UPDATE_FAILED']
    for status in status_list:
        status_candidate.remove(status)
    for status in status_candidate:
        filters.append(
            {
                'Key': 'Status',
                'Value': status,
                'Condition': 'IS_NOT'
            }
        )
    for page in paginator.paginate(Filters=filters):
        for item in page['Forecasts']:
            forecast_arn = item['ForecastArn']
            result = compiled_pattern.match(forecast_arn)
            if result:
                # Check if the forecast is associated to the target project.
                retrieved_project_name = result.group(1)
                if retrieved_project_name == project_name:
                    deletion_target_forecast_arns.append(forecast_arn)

    logger.info({
        'message': 'get_deletion_target_forecast_arns() completed',
        'project_name': project_name,
        'status_list': status_list,
        'result': deletion_target_forecast_arns
    })
    return deletion_target_forecast_arns


@lambda_handler_logger(logger=logger, lambda_name='delete_outdated_forecasts')
def lambda_handler(event, _):
    """
    Lambda function handler
    """
    target_forecast_arns = get_deletion_target_forecast_arns(
        event['ProjectName'], ['ACTIVE', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED'])

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
    deleting_forecast_arns = get_deletion_target_forecast_arns(
        event['ProjectName'], ['DELETE_PENDING', 'DELETE_IN_PROGRESS'])
    if len(deleting_forecast_arns) > 0:
        logger.info({
            'message': 'these resources are deleting.',
            'deleting_forecast_arns': deleting_forecast_arns
        })
        raise actions.ResourcePending

    logger.info({
        'message': 'forecasts deleted',
    })

    return event

"""
Initialize update forecast flow.
"""
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from init_basic_params import init_basic_params  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

logger = Logger()
forecast_client = boto3.client('forecast')


@init_basic_params()
@lambda_handler_logger(logger=logger, lambda_name='init_update_forecast_flow')
def lambda_handler(event, _):
    """
    Lambda function handler
    """

    # Set DS/DSG name/arn

    return event

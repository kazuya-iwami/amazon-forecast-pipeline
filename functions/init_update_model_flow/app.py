"""
Initialize update model flow.
"""
from datetime import datetime
from os import environ
import boto3
# From Lambda Layers
from load_params import load_params  # pylint: disable=import-error
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error


logger = Logger()
forecast_client = boto3.client('forecast')


@lambda_handler_logger(logger=logger, lambda_name='init_update_model_flow')
def lambda_handler(event, _):
    """
    Lambda function handler
    """
    # Setup params
    #   Replace hyphen of stack_name to underscore because some resource names do not support hyphen.
    event['ProjectName'] = environ['STACK_NAME'].replace(
        '-', '_')
    event['AccountID'] = boto3.client(
        'sts').get_caller_identity()['Account']
    event['Region'] = environ['AWS_REGION']

    event['TriggeredAt'] = datetime.now().strftime(
        "%Y_%m_%d_%H_%M_%S")
    event['TraceId'] = event['StateMachineName'] + \
        '_' + event['TriggeredAt']

    # Update trace_id of logger
    logger.structure_logs(
        append=True, trace_id=event['TraceId'])

    logger.info({
        'message': 'loading "params.json"',
    })
    params = load_params()
    logger.info({
        'message': 'loaded "params.json" successfully',
        'params': params
    })
    event.update(params)

    logger.info({
        'message': 'finish initializing'
    })
    return event

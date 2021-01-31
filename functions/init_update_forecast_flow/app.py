"""
Initialize update model flow.
"""
import datetime
from os import environ
import re
import boto3
# From Lambda Layers
from load_params import load_params  # pylint: disable=import-error
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

PREDICTOR_PATTERN = r'^arn:aws:forecast:.+?:.+?:predictor\/(.+?)_([0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2})'

logger = Logger()
forecast_client = boto3.client('forecast')
compiled_predictor_pattern = re.compile(PREDICTOR_PATTERN)


@lambda_handler_logger(logger=logger, lambda_name='init_update_forecast_flow')
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

    event['TriggeredAt'] = datetime.datetime.now().strftime(
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

    # Get the latest predictor. This is used in create_forecast Lambda function.

    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/forecast.html#ForecastService.Client.list_predictors
    paginator = forecast_client.get_paginator('list_predictors')
    filters = [{
        'Key': 'Status',
        'Value': 'ACTIVE',
        'Condition': 'IS'
    }]
    candidates = []
    for page in paginator.paginate(Filters=filters):
        for item in page['Predictors']:
            predictor_arn = item['PredictorArn']
            result = compiled_predictor_pattern.match(predictor_arn)
            if result:
                # Check if the predictor is associated to the target project.
                project_name = result.group(1)
                if project_name == event['ProjectName']:
                    dt = datetime.datetime.strptime(
                        result.group(2), '%Y_%m_%d_%H_%M_%S')
                    candidates.append({'arn': predictor_arn, 'dt': dt})

    # Get the latest predictor
    latest_predictor_arn = ''
    sorted_candidates = sorted(candidates, key=lambda x: x['dt'])
    if len(sorted_candidates) > 0:
        latest_predictor_arn = sorted_candidates[-1]['arn']
    else:
        # If there has not been any predictor, finish update_model_flow.
        raise Exception(
            'the latest predictor not found. the 1st execution of update-model statemachine has not been completed yet.')

    event['LatestPredictorArn'] = latest_predictor_arn

    # Get datasets associated to the latest predictor (predictor -> dataset import job -> datasets). This is used in create_dataset_import_job Lambda function.

    response = forecast_client.describe_predictor(
        PredictorArn=latest_predictor_arn
    )
    logger.info({
        'message': 'forecast_client.describe_predictor called',
        'response': response
    })

    dataset_import_job_arns = response['DatasetImportJobArns']

    for job_arn in dataset_import_job_arns:
        response = forecast_client.describe_dataset_import_job(
            DatasetImportJobArn=job_arn
        )
        logger.info({
            'message': 'forecast_client.describe_dataset_import_job called',
            'response': response
        })
        dataset_arn = response['DatasetArn']

        response = forecast_client.describe_dataset(
            DatasetArn=dataset_arn
        )
        logger.info({
            'message': 'forecast_client.describe_dataset called',
            'response': response
        })
        dataset_type = response['DatasetType']
        dataset_name = response['DatasetName']

        for dataset in event['Datasets']:
            if dataset['DatasetType'] == dataset_type:
                dataset['DatasetArn'] = dataset_arn
                dataset['DatasetName'] = dataset_name

    logger.info({
        'message': 'finish initializing'
    })
    return event

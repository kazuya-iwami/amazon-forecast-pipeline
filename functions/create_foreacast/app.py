"""
Creates a forecast for each item in the target_time_series dataset.
"""
from os import environ
import re
import datetime
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

FORECAST_NAME = '{project_name}_{date}'
FORECAST_ARN = 'arn:aws:forecast:{region}:{account}:forecast/{forecast_name}'

PREDICTOR_PATTERN = r'^arn:aws:forecast:.+?:.+?:predictor\/(.+?)_([0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2})'

logger = Logger()
forecast_client = boto3.client('forecast')
compiled_pattern = re.compile(PREDICTOR_PATTERN)


def get_latest_predictor_arn(project_name):
    """
    Get the latest predictor ARN.
    """
    response = forecast_client.list_predictors(
        Filters=[
            {
                'Key': 'Status',
                'Value': 'ACTIVE',
                'Condition': 'IS'
            },
        ]
    )
    logger.info({
        'message': 'forecast_client.list_predictors called',
        'response': response,
    })

    predictor_arns = [predictor['PredictorArn']
                      for predictor in response['Predictors']]
    target_candidates = []

    # List up outdated predictors associated to the target project excluding the latest two.
    for predictor_arn in predictor_arns:
        result = compiled_pattern.match(predictor_arn)
        if result:
            # Check if the forecast is associated to the target project.
            retrieved_project_name = result.group(1)
            if retrieved_project_name == project_name:
                dt = datetime.datetime.strptime(
                    result.group(2), '%Y_%m_%d_%H_%M_%S')
                target_candidates.append({'arn': predictor_arn, 'dt': dt})

    # Get the latest predictor
    target_predictor_arn = None
    sorted_target_candidates = sorted(target_candidates, key=lambda x: x['dt'])
    if len(sorted_target_candidates) > 0:
        target_predictor_arn = sorted_target_candidates[-1]

    logger.info({
        'message': 'get_latest_predictor_arn() completed',
        'project_name': project_name,
        'result': target_predictor_arn,
        'sorted_target_candidates': sorted_target_candidates,

    })
    return target_predictor_arn


def lambda_handler(event, _):
    """
    Lambda function handler
    """
    logger.structure_logs(
        append=False, lambda_name='create_foreacast', trace_id=event['TraceId'])
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
        latest_predictor_arn = get_latest_predictor_arn(event['ProjectName'])
        if latest_predictor_arn is None:
            logger.warn({
                'message': 'the latest predictor not found. the 1st execution of update-model statemachine has not been completed yet.',
            })
            raise Exception(
                'the latest predictor not found. the 1st execution of update-model statemachine has not been completed yet.')

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
        'message': 'forecast was created successfully',
        'forecast_arn': event['ForecastArn']
    })

    return event

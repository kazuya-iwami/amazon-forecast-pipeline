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

PATTERN = r'^arn:aws:forecast:.+?:.+?:predictor\/(.+?)_([0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2})'

logger = Logger()
forecast_client = boto3.client('forecast')
compiled_pattern = re.compile(PATTERN)


def list_predictor_arns(project_name, status):
    """
    List predictor ARNs.
    """
    response = forecast_client.list_predictors(
        Filters=[
            {
                'Key': 'Status',
                'Value': status,
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

    # List up predictors associated to the target project.
    for predictor_arn in predictor_arns:
        result = compiled_pattern.match(predictor_arn)
        if result:
            # Check if the forecast is associated to the target project.
            retrieved_project_name = result.group(1)
            if retrieved_project_name == project_name:
                dt = datetime.datetime.strptime(
                    result.group(2), '%Y_%m_%d_%H_%M_%S')
                target_candidates.append({'arn': predictor_arn, 'dt': dt})
    logger.info({
        'message': 'list_predictor_arns() completed',
        'project_name': project_name,
        'status': status,
        'result': target_candidates,
    })
    return target_candidates


def list_deletion_target_predictor_arns(project_name):
    """
    List deletion target predictors, which are Active predictors except for the latest two
    """
    target_candidates = list_predictor_arns(project_name, 'ACTIVE')

    # Ingore the latest two predictors
    # because some existing forecasts may be associated to the previous predictor.
    sorted_target_candidates = sorted(target_candidates, key=lambda x: x['dt'])
    target_predictor_arns = [predictor['arn']
                             for predictor in sorted_target_candidates[:-2]]

    logger.info({
        'message': 'list_deletion_target_predictor_arns() completed',
        'project_name': project_name,
        'result': target_predictor_arns,
        'sorted_target_candidates': sorted_target_candidates,
    })
    return target_predictor_arns


@lambda_handler_logger(logger=logger, lambda_name='delete_outdated_predictors')
def lambda_handler(event, _):
    """
    Lambda function handler
    """
    # List deletion target predictors, which is Active predoctors except for the latest two.
    target_predictor_arns = list_deletion_target_predictor_arns(
        event['ProjectName'])

    # Delete resources
    for predictor_arn in target_predictor_arns:
        try:
            response = forecast_client.delete_predictor(
                PredictorArn=predictor_arn
            )
            logger.info({
                'message': 'forecast_client.delete_predictor called',
                'response': response
            })
        except forecast_client.exceptions.ResourceNotFoundException:
            logger.warn({
                'message': 'Predictor has already been deleted',
                'predictor_arn': predictor_arn
            })

    # When the resource is in DELETE_PENDING or DELETE_IN_PROGRESS,
    # ResourcePending exception will be thrown and this Lambda function will be retried.
    deleting_predictor_arns = \
        list_predictor_arns(event['ProjectName'], 'DELETE_PENDING') + \
        list_predictor_arns(event['ProjectName'], 'DELETE_IN_PROGRESS')
    if len(deleting_predictor_arns) != 0:
        logger.info({
            'message': 'these resources are deleting.',
            'deleting_predictor_arns': deleting_predictor_arns
        })
        raise actions.ResourcePending

    return event

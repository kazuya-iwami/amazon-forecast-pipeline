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

DATASET_GROUP_PATTERN = r'^arn:aws:forecast:.+?:.+?:dataset-group\/(.+?)_([0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2})'

logger = Logger()
forecast_client = boto3.client('forecast')
compiled_dataset_group_pattern = re.compile(DATASET_GROUP_PATTERN)


def get_deletion_target_dataset_group_arns(project_name):
    """
    Get dataset group ARNs which should be deleted. The dataset groups except for the latest two are eligible for deletion.
    """
    # Get all dataset groups
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/forecast.html#ForecastService.Paginator.ListDatasetGroups
    paginator = forecast_client.get_paginator('list_dataset_groups')
    dataset_group_arns = []
    for page in paginator.paginate():
        dataset_group_arns.extend([item['DatasetGroupArn']
                                   for item in page['DatasetGroups']])

    candidate_dataset_groups = []

    for dataset_group_arn in dataset_group_arns:
        result = compiled_dataset_group_pattern.match(dataset_group_arn)
        if result:
            retrieved_project_name = result.group(1)
            if retrieved_project_name == project_name:
                dt = datetime.datetime.strptime(
                    result.group(2), '%Y_%m_%d_%H_%M_%S')
                candidate_dataset_groups.append(
                    {'arn': dataset_group_arn, 'dt': dt})

    candidate_dataset_groups = sorted(
        candidate_dataset_groups, key=lambda x: x['dt'])

    deletion_target_dataset_group_arns = [dataset_group['arn']
                                          for dataset_group in candidate_dataset_groups[:-2]]

    logger.info({
        'message': 'get_deletion_target_dataset_group_arns() completed',
        'project_name': project_name,
        'result': deletion_target_dataset_group_arns
    })

    return deletion_target_dataset_group_arns


def get_deletion_target_predictor_arns(project_name, status_list):
    """
    Get predictor ARNs which should be deleted. The predictors associated to deletion target dataset groups are eligible for deletion.
    """
    deletion_target_predictor_arns = []
    # Get deletion target dataset groups
    dataset_group_arns = get_deletion_target_dataset_group_arns(project_name)

    # Get all predictors
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/forecast.html#ForecastService.Client.list_predictors
    paginator = forecast_client.get_paginator('list_predictors')
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
        for item in page['Predictors']:
            if item['DatasetGroupArn'] in dataset_group_arns:
                # This predircor is deletion target
                deletion_target_predictor_arns.append(item['PredictorArn'])

    logger.info({
        'message': 'get_deletion_target_predictor_arns() completed',
        'project_name': project_name,
        'status_list': status_list,
        'result': deletion_target_predictor_arns
    })
    return deletion_target_predictor_arns


@lambda_handler_logger(logger=logger, lambda_name='delete_outdated_predictors')
def lambda_handler(event, _):
    """
    Lambda function handler
    """
    deletion_target_predictor_arns = get_deletion_target_predictor_arns(
        event['ProjectName'], ['ACTIVE', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED'])

    # Delete resources
    for predictor_arn in deletion_target_predictor_arns:
        try:
            response = forecast_client.delete_predictor(
                PredictorArn=predictor_arn
            )
            logger.info({
                'message': 'forecast_client.delete_predictor called',
                'response': response,
                'predictor_arn': predictor_arn
            })
        except forecast_client.exceptions.ResourceNotFoundException:
            logger.warn({
                'message': 'predictor has already been deleted',
                'predictor_arn': predictor_arn
            })

    # When the resource is in DELETE_PENDING or DELETE_IN_PROGRESS,
    # ResourcePending exception will be thrown and this Lambda function will be retried.
    deleting_predictors = get_deletion_target_predictor_arns(
        event['ProjectName'], ['DELETE_PENDING', 'DELETE_IN_PROGRESS'])
    if len(deleting_predictors) > 0:
        logger.info({
            'message': 'some resources are deleting.',
            'deleting_predictors': deleting_predictors
        })
        raise actions.ResourcePending

    logger.info({
        'message': 'predictors deleted',
    })
    return event

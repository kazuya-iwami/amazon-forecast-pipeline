"""
Delete outdated datasets.
"""
import re
import datetime
import boto3
# From Lambda Layers
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

DATASET_GROUP_PATTERN = r'^arn:aws:forecast:.+?:.+?:dataset-group\/(.+?)_([0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2})'

logger = Logger()
forecast_client = boto3.client('forecast')
compiled_dataset_group_pattern = re.compile(DATASET_GROUP_PATTERN)


def get_deletion_target_dataset_group_arns(project_name):
    """
    Get dataset group ARNs which should be deleted. The dataset groups except for the latest two are target.
    """
    # Get all dataset grousps
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


def get_deletion_target_dataset_arns(project_name):
    """
    Get dataset ARNs which should be deleted. The datasets that associated to deletion target dataset groups are target.
    """
    deletion_target_dataset_arns = []

    # Get deletion target dataset group ARNs
    dataset_group_arns = get_deletion_target_dataset_group_arns(project_name)

    for dataset_group_arn in dataset_group_arns:
        response = forecast_client.describe_dataset_group(
            DatasetGroupArn=dataset_group_arn)
        deletion_target_dataset_arns.extend(response['DatasetArns'])

    logger.info({
        'message': 'get_deletion_target_dataset_arns() completed',
        'project_name': project_name,
        'result': deletion_target_dataset_arns
    })
    return deletion_target_dataset_arns


@lambda_handler_logger(logger=logger, lambda_name='delete_outdated_datasets')
def lambda_handler(event, _):
    """
    Lambda function handler
    """
    deletion_target_dataset_arns = get_deletion_target_dataset_arns(
        event['ProjectName'])

    # Delete resources
    for dataset_arn in deletion_target_dataset_arns:
        try:
            response = forecast_client.delete_dataset(
                DatasetArn=dataset_arn
            )
            logger.info({
                'message': 'forecast_client.delete_dataset called',
                'response': response
            })
        except forecast_client.exceptions.ResourceNotFoundException:
            logger.warn({
                'message': 'dataset has already been deleted',
                'dataset_arn': dataset_arn
            })

    logger.info({
        'message': 'datasets deleted',
        'deletion_target_dataset_arns': deletion_target_dataset_arns
    })

    return event

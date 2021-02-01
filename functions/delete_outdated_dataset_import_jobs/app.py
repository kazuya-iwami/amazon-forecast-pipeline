"""
Delete outdated import jobs
"""
import re
import datetime
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error


DATASET_GROUP_PATTERN = r'^arn:aws:forecast:.+?:.+?:dataset-group\/(.+?)_([0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2})'
DATASET_PATTERN = r'^arn:aws:forecast:.+?:.+?:dataset\/(.+?)$'
IMPORT_JOB_PATTERN = r'^arn:aws:forecast:.+?:.+?:dataset-import-job\/(.+?)/.+?'

logger = Logger()
forecast_client = boto3.client('forecast')
compiled_import_job_pattern = re.compile(IMPORT_JOB_PATTERN)
compiled_dataset_pattern = re.compile(DATASET_PATTERN)
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


def get_deletion_target_dataset_arns(project_name):
    """
    Get dataset ARNs which should be deleted. The datasets associated to deletion target dataset groups are eligible for deletion.
    """
    deletion_target_dataset_arns = []

    # Get deletion target dataset groups
    dataset_group_arns = get_deletion_target_dataset_group_arns(project_name)

    # Get datasets associated to the deletion target
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


def get_deletion_target_dataset_import_job_arns(project_name, status_list):
    """
    Get dataset import job ARNs which should be deleted. The dataset import jobs associated to deletion target datasets are eligible for deletion.
    """
    deletion_target_dataset_import_job_arns = []

    # Get deletion target dataset names
    deletion_target_dataset_names = []
    dataset_arns = get_deletion_target_dataset_arns(
        project_name)
    for dataset_arn in dataset_arns:
        result = compiled_dataset_pattern.match(
            dataset_arn)
        if result:
            name = result.group(1)
            deletion_target_dataset_names.append(name)

    # Get all dataset import jobs
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/forecast.html#ForecastService.Paginator.ListDatasetImportJobs
    paginator = forecast_client.get_paginator('list_dataset_import_jobs')
    dataset_import_job_arns = []
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
        dataset_import_job_arns.extend([item['DatasetImportJobArn']
                                        for item in page['DatasetImportJobs']])

    # Get dataset import jobs that associated to deletion target datasets
    for dataset_import_job_arn in dataset_import_job_arns:
        result = compiled_import_job_pattern.match(
            dataset_import_job_arn)
        if result:
            retrieved_dataset_name = result.group(1)
            if retrieved_dataset_name in deletion_target_dataset_names:
                deletion_target_dataset_import_job_arns.append(
                    dataset_import_job_arn)

    logger.info({
        'message': 'get_deletion_target_dataset_import_job_arns() completed',
        'project_name': project_name,
        'status_list': status_list,
        'result': deletion_target_dataset_import_job_arns
    })

    return deletion_target_dataset_import_job_arns


@lambda_handler_logger(logger=logger, lambda_name='delete_outdated_dataset_import_jobs')
def lambda_handler(event, _):
    """
    Lambda function handler
    """
    deletion_target_dataset_import_job_arns = get_deletion_target_dataset_import_job_arns(
        event['ProjectName'], ['ACTIVE', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED'])

    # Delete resources
    for import_job_arn in deletion_target_dataset_import_job_arns:
        try:
            response = forecast_client.delete_dataset_import_job(
                DatasetImportJobArn=import_job_arn
            )
            logger.info({
                'message': 'forecast_client.delete_dataset_import_job called',
                'response': response,
                'import_job_arn': import_job_arn
            })
        except forecast_client.exceptions.ResourceNotFoundException:
            logger.warn({
                'message': 'Import job has already been deleted',
                'import_job_arn': import_job_arn
            })

    # When the resource is in DELETE_PENDING or DELETE_IN_PROGRESS,
    # ResourcePending exception will be thrown and this Lambda function will be retried.
    deleting_dataset_import_jobs = get_deletion_target_dataset_import_job_arns(
        event['ProjectName'], ['DELETE_PENDING', 'DELETE_IN_PROGRESS'])
    if len(deleting_dataset_import_jobs) > 0:
        logger.info({
            'message': 'some resources are deleting.',
            'deleting_dataset_import_job_arns': deleting_dataset_import_jobs
        })
        raise actions.ResourcePending

    logger.info({
        'message': 'dataset import jobs deleted',
    })
    return event

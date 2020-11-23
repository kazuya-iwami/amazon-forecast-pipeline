"""
Delete outdated forecast export jobs
"""
import re
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

PATTERN = r'^arn:aws:forecast:.+?:.+?:forecast-export-job\/(.+?)_[0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}\/.+?'

logger = Logger()
forecast_client = boto3.client('forecast')
compiled_pattern = re.compile(PATTERN)


def list_target_export_job_arns(project_name, status):
    """
    List export job ARNs which should be deleted.
    """
    response = forecast_client.list_forecast_export_jobs(
        Filters=[
            {
                'Key': 'Status',
                'Value': status,
                'Condition': 'IS'
            },
        ]
    )
    logger.info({
        'message': 'forecast_client.list_forecast_export_jobs called',
        'response': response
    })
    export_job_arns = [job['ForecastExportJobArn']
                       for job in response['ForecastExportJobs']]

    target_export_job_arns = []

    for job_arn in export_job_arns:
        result = compiled_pattern.match(job_arn)
        if result:
            # Check if the export-job is associated to the target project.
            retrieved_project_name = result.group(1)
            if retrieved_project_name == project_name:
                target_export_job_arns.append(job_arn)
    logger.info({
        'message': 'list_target_export_job_arns() completed',
        'project_name': project_name,
        'status': status,
        'result': target_export_job_arns
    })
    return target_export_job_arns


def lambda_handler(event, _):
    """
    Lambda function handler
    """
    logger.structure_logs(
        append=False, lambda_name='delete_outdated_foreast_export_jobs', trace_id=event['TraceId'])
    logger.info({'message': 'Event received', 'event': event})

    target_export_job_arns = list_target_export_job_arns(
        event['ProjectName'], 'ACTIVE')

    # Delete resources
    for job_arn in target_export_job_arns:
        try:
            # https://docs.aws.amazon.com/forecast/latest/dg/API_DeleteForecastExportJob.html
            response = forecast_client.delete_forecast_export_job(
                ForecastExportJobArn=job_arn
            )
            logger.info({
                'message': 'forecast_client.delete_forecast_export_job called',
                'response': response
            })
        except forecast_client.exceptions.ResourceNotFoundException:
            logger.warn({
                'message': 'ForecastExportJob has already been deleted',
                'export_job_arn': job_arn
            })

    # When the resource is in DELETE_PENDING or DELETE_IN_PROGRESS,
    # ResourcePending exception will be thrown and this Lambda function will be retried.
    deleting_export_job_arns = \
        list_target_export_job_arns(event['ProjectName'], 'DELETE_PENDING') + \
        list_target_export_job_arns(event['ProjectName'], 'DELETE_IN_PROGRESS')
    if len(deleting_export_job_arns) != 0:
        logger.info({
            'message': 'these resources are deleting.',
            'deleting_export_job_arns': deleting_export_job_arns
        })
        raise actions.ResourcePending

    return event

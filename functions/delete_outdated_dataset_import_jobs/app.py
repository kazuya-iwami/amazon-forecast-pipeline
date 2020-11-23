"""
Delete outdated import jobs
"""
import re
import datetime
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

IMPORT_JOB_PATTERN = r'^arn:aws:forecast:.+?:.+?:dataset-import-job\/(.+?)_(TARGET_TIME_SERIES|RELATED_TIME_SERIES|ITEM_METADATA)\/.+?'
PREDICTOR_PATTERN = r'^arn:aws:forecast:.+?:.+?:predictor\/(.+?)_([0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2})'

logger = Logger()
forecast_client = boto3.client('forecast')
import_job_compiled_pattern = re.compile(IMPORT_JOB_PATTERN)
predictor_compiled_pattern = re.compile(PREDICTOR_PATTERN)


def list_preserved_import_job_arns(project_name):
    """
    List predictor ARNs which should be preserved.
    """
    # list up the latest two predictors.
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
        'response': response
    })
    predictor_arns = [predictor['PredictorArn']
                      for predictor in response['Predictors']]
    preserved_predictor_candidates = []

    for predictor_arn in predictor_arns:
        result = predictor_compiled_pattern.match(predictor_arn)
        if result:
            # Check if the forecast is associated to the target project.
            retrieved_project_name = result.group(1)
            if retrieved_project_name == project_name:
                dt = datetime.datetime.strptime(
                    result.group(2), '%Y_%m_%d_%H_%M_%S')
                preserved_predictor_candidates.append(
                    {'arn': predictor_arn, 'dt': dt})

    # Pick up the latest two predictors' ARNS (preserved_predictor_arns) if they exist.
    preserved_predictor_arns = []
    preserved_predictor_candidates = sorted(
        preserved_predictor_candidates, key=lambda x: x['dt'])
    preserved_predictor_arns = [predictor['arn']
                                for predictor in preserved_predictor_candidates[-2:]]
    logger.info({
        'message': 'Get preserved_predictor_arns in list_preserved_import_job_arns()',
        'preserved_predictor_arns': preserved_predictor_arns
    })

    # List up import jobs which are associated to the latest two predictors
    preserved_import_job_arns = []
    for predictor_arn in preserved_predictor_arns:
        response = forecast_client.describe_predictor(
            PredictorArn=predictor_arn
        )
        logger.info({
            'message': 'forecast_client.describe_predictor called',
            'response': response
        })
        preserved_import_job_arns = preserved_import_job_arns + \
            response['DatasetImportJobArns']

    logger.info({
        'message': 'list_preserved_import_job_arns() completed',
        'project_name': project_name,
        'result': preserved_import_job_arns,
        'preserved_predictor_arns': preserved_predictor_arns
    })
    return preserved_import_job_arns


def list_target_import_job_arns(project_name, status):
    response = forecast_client.list_dataset_import_jobs(
        Filters=[
            {
                'Key': 'Status',
                'Value': status,
                'Condition': 'IS'
            },
        ]
    )
    logger.info({
        'message': 'forecast_client.list_dataset_import_jobs called',
        'response': response
    })
    import_job_arns = [job['DatasetImportJobArn']
                       for job in response['DatasetImportJobs']]

    target_import_job_candidates = []

    for import_job_arn in import_job_arns:
        result = import_job_compiled_pattern.match(import_job_arn)
        if result:
            # Check if the import job is associated to the target project.
            retrieved_project_name = result.group(1)
            if retrieved_project_name == project_name:
                target_import_job_candidates.append(import_job_arn)

    # Exclude preserved_import_job_arns
    preserved_import_job_arns = set(
        list_preserved_import_job_arns(project_name))
    target_import_job_candidates = set(target_import_job_candidates)

    target_import_job_arns = list(
        target_import_job_candidates - preserved_import_job_arns)

    logger.info({
        'message': 'list_target_import_job_arns() completed',
        'result': target_import_job_arns,
        'project_name': project_name,
        'status': status,
        'preserved_import_job_arns': preserved_import_job_arns,
        'target_import_job_candidates': target_import_job_candidates
    })
    return target_import_job_arns


def lambda_handler(event, _):
    """
    Lambda function handler
    """
    logger.structure_logs(
        append=True, lambda_name='delete_outdated_dataset_import_jobs', trace_id=event['CurrentDate'])
    logger.info({'message': 'Event received', 'event': event})

    target_import_job_arns = list_target_import_job_arns(
        event['ProjectName'], 'ACTIVE')

    # Delete resources
    for import_job_arn in target_import_job_arns:
        try:
            response = forecast_client.delete_dataset_import_job(
                DatasetImportJobArn=import_job_arn
            )
            logger.info({
                'message': 'forecast_client.delete_dataset_import_job called',
                'response': response
            })
        except forecast_client.exceptions.ResourceNotFoundException:
            logger.warn({
                'message': 'Import job has already been deleted',
                'import_job_arn': import_job_arn
            })

    # When the resource is in DELETE_PENDING or DELETE_IN_PROGRESS,
    # ResourcePending exception will be thrown and this Lambda function will be retried.
    deleting_import_job_arns = \
        list_target_import_job_arns(event['ProjectName'], 'DELETE_PENDING') + \
        list_target_import_job_arns(
            event['ProjectName'], 'DELETE_IN_PROGRESS')
    if len(deleting_import_job_arns) != 0:
        logger.info({
            'message': 'these resources are deleting.',
            'deleting_import_job_arns': deleting_import_job_arns
        })
        raise actions.ResourcePending

    return event

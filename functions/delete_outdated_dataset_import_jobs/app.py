"""
Delete outdated datasetImportJobs.
"""
import boto3
# From Lambda Layers
from aws_lambda_powertools import Logger  # pylint: disable=import-errosr

logger = Logger()
forecast_client = boto3.client('forecast')


def lambda_handler(event, _):
    """
    Lambda function handler
    """
    logger.info({'message': 'Event received', 'event': event})

    # TODO: Support multi datasets
    response = forecast_client.list_dataset_import_jobs(
        Filters=[
            {
                'Key': 'DatasetArn',
                'Value': event['DatasetArn'],
                'Condition': 'IS'
            },
            {
                'Key': 'Status',
                'Value': 'ACTIVE',
                'Condition': 'IS'
            },
        ]
    )
    logger.info({
        'message': 'forecast_client.describe_dataset_import_job called',
        'response': response
    })
    import_jobs = response['DatasetImportJobs']

    # List

    # # TODO: Support multiple datasets
    # event['DatasetImportJobName'] = IMPORT_JOB_NAME.format(
    #     dataset_name=event['DatasetName'],
    #     date=event['CurrentDate']
    # )
    # event['DatasetImportJobArn'] = IMPORT_JOB_ARN.format(
    #     region=environ['AWS_REGION'],
    #     account=event['AccountID'],
    #     dataset_name=event['DatasetName'],
    #     import_job_name=event['DatasetImportJobName']
    # )
    # try:
    #     response = forecast_client.describe_dataset_import_job(
    #         DatasetImportJobArn=event['DatasetImportJobArn']
    #     )
    #     logger.info({
    #         'message': 'forecast_client.describe_dataset_import_job called',
    #         'response': response
    #     })

    # except forecast_client.exceptions.ResourceNotFoundException:
    #     logger.info(
    #         'Dataset import job not found. Creating new job.'
    #     )

    #     response = forecast_client.create_dataset_import_job(
    #         DatasetImportJobName=event['DatasetImportJobName'],
    #         DatasetArn=event['DatasetArn'],
    #         DataSource={
    #             'S3Config':
    #                 {
    #                     'Path':
    #                         's3://{bucket}/{folder}/{file}'.format(
    #                             bucket=environ['S3_BUCKET_NAME'],
    #                             folder=environ['S3_SRC_FOLDER'],
    #                             file=environ['TARGET_TIME_SERIES_FILE_NAME']
    #                         ),
    #                     'RoleArn':
    #                         environ['FORECAST_IMPORT_JOB_ROLE_ARN']
    #                 }
    #         },
    #         TimestampFormat=event['TimestampFormat']
    #     )
    #     logger.info({
    #         'message': 'forecast_client.create_dataset_import_job called',
    #         'response': response
    #     })

    #     response = forecast_client.describe_dataset_import_job(
    #         DatasetImportJobArn=event['DatasetImportJobArn']
    #     )
    #     logger.info({
    #         'message': 'forecast_client.describe_dataset_import_job called',
    #         'response': response
    #     })

    # # When the resource is in CREATE_PENDING or CREATE_IN_PROGRESS,
    # # ResourcePending exception will be thrown and this Lambda function will be retried.
    # actions.take_action(response['Status'])
    # return event

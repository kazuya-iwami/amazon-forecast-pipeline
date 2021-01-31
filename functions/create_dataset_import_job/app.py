"""
Uploads your training data to an Amazon Forecast dataset.
"""
from os import environ
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

IMPORT_JOB_NAME = 'job_{date}'
IMPORT_JOB_ARN = 'arn:aws:forecast:{region}:{account}:dataset-import-job/{dataset_name}' \
    '/{import_job_name}'

logger = Logger()
forecast_client = boto3.client('forecast')


@lambda_handler_logger(logger=logger, lambda_name='create_dataset_import_job')
def lambda_handler(event, _):
    """
    Lambda function handler
    """

    import_job_arns = []

    # In this sample, creating dataset import job sequentially because default limit of 'Maximum parallel running CreateDatasetImportJob tasks' is small. You should increase this limit to create dataset import job in parallel.
    # https://docs.aws.amazon.com/forecast/latest/dg/limits.html

    for dataset in event['Datasets']:
        dataset_name = dataset['DatasetName']
        dataset_arn = dataset['DatasetArn']
        import_job_name = IMPORT_JOB_NAME.format(
            date=event['TriggeredAt']
        )
        import_job_arn = IMPORT_JOB_ARN.format(
            region=event['Region'],
            account=event['AccountID'],
            dataset_name=dataset_name,
            import_job_name=import_job_name
        )
        import_job_arns.append(import_job_arn)

        filename = ''
        for job in event['DatasetImportJobs']:
            if job['DatasetType'] == dataset['DatasetType']:
                filename = job['Filename']
        if filename == '':
            raise Exception(
                'failed to find "Filename" for dataset import job.')
        try:
            response = forecast_client.describe_dataset_import_job(
                DatasetImportJobArn=import_job_arn
            )
            logger.info({
                'message': 'forecast_client.describe_dataset_import_job called',
                'response': response,
                'dataset_import_job_arn': import_job_arn
            })

        except forecast_client.exceptions.ResourceNotFoundException:
            logger.info({
                'message': 'creating new dataset import job',
                'dataset_import_job_arn': import_job_arn
            })

            response = forecast_client.create_dataset_import_job(
                DatasetImportJobName=import_job_name,
                DatasetArn=dataset_arn,
                DataSource={
                    'S3Config':
                        {'Path':
                            's3://{bucket}/{folder}/{file}'.format(
                                bucket=environ['S3_BUCKET_NAME'],
                                folder=environ['S3_SRC_FOLDER'],
                                file=filename
                            ),
                            'RoleArn':
                                environ['FORECAST_IMPORT_JOB_ROLE_ARN']
                         }
                },
                TimestampFormat=event['DatasetTimestampFormat']
            )
            logger.info({
                'message': 'forecast_client.create_dataset_import_job called',
                'response': response,
                'dataset_import_job_arn': import_job_arn
            })

            response = forecast_client.describe_dataset_import_job(
                DatasetImportJobArn=import_job_arn
            )
            logger.info({
                'message': 'forecast_client.describe_dataset_import_job called',
                'response': response,
                'dataset_import_job_arn': import_job_arn
            })

        # When the resource is in CREATE_PENDING or CREATE_IN_PROGRESS, ResourcePending exception will be thrown and this Lambda function will be retried.
        actions.take_action(response['Status'])

    logger.info({
        'message': 'dataset import job was created',
        'dataset_import_job_arns': import_job_arns
    })

    return event

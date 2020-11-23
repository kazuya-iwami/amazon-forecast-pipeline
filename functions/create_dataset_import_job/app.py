"""
Uploads your training data to an Amazon Forecast dataset.
"""
from os import environ
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

IMPORT_JOB_NAME = '{dataset_name}_{date}'
IMPORT_JOB_ARN = 'arn:aws:forecast:{region}:{account}:dataset-import-job/{dataset_name}' \
    '/{import_job_name}'

logger = Logger()
forecast_client = boto3.client('forecast')


@lambda_handler_logger(logger=logger, lambda_name='create_dataset_import_job')
def lambda_handler(event, _):
    """
    Lambda function handler
    """

    # TODO: Support multiple datasets
    event['DatasetImportJobName'] = IMPORT_JOB_NAME.format(
        dataset_name=event['DatasetName'],
        date=event['CurrentDate']
    )
    event['DatasetImportJobArn'] = IMPORT_JOB_ARN.format(
        region=event['Region'],
        account=event['AccountID'],
        dataset_name=event['DatasetName'],
        import_job_name=event['DatasetImportJobName']
    )
    try:
        response = forecast_client.describe_dataset_import_job(
            DatasetImportJobArn=event['DatasetImportJobArn']
        )
        logger.info({
            'message': 'forecast_client.describe_dataset_import_job called',
            'response': response
        })

    except forecast_client.exceptions.ResourceNotFoundException:
        logger.info({
            'message': 'creating new dataset import job',
            'dataset_import_job_arn': event['DatasetImportJobArn']
        })

        response = forecast_client.create_dataset_import_job(
            DatasetImportJobName=event['DatasetImportJobName'],
            DatasetArn=event['DatasetArn'],
            DataSource={
                'S3Config':
                    {
                        'Path':
                            's3://{bucket}/{folder}/{file}'.format(
                                bucket=environ['S3_BUCKET_NAME'],
                                folder=environ['S3_SRC_FOLDER'],
                                file=environ['TARGET_TIME_SERIES_FILE_NAME']
                            ),
                        'RoleArn':
                            environ['FORECAST_IMPORT_JOB_ROLE_ARN']
                    }
            },
            TimestampFormat=event['TimestampFormat']
        )
        logger.info({
            'message': 'forecast_client.create_dataset_import_job called',
            'response': response
        })

        response = forecast_client.describe_dataset_import_job(
            DatasetImportJobArn=event['DatasetImportJobArn']
        )
        logger.info({
            'message': 'forecast_client.describe_dataset_import_job called',
            'response': response
        })

    # When the resource is in CREATE_PENDING or CREATE_IN_PROGRESS,
    # ResourcePending exception will be thrown and this Lambda function will be retried.
    actions.take_action(response['Status'])

    logger.info({
        'message': 'dataset import job was created',
        'dataset_import_job_arn': event['DatasetImportJobArn']
    })

    return event

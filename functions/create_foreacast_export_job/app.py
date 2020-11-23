"""
Export a result of forecast into S3 bucket
"""
from os import environ
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

FORECAST_EXPORT_JOB_NAME = '{project_name}_{date}'
FORECAST_EXPORT_JOB_ARN = 'arn:aws:forecast:{region}:{account}:forecast-export-job/' \
    '{forecast_name}/{export_job_name}'

logger = Logger()
forecast_client = boto3.client('forecast')


@lambda_handler_logger(logger=logger, lambda_name='create_foreacast_export_job')
def lambda_handler(event, _):
    """
    Lambda function handler
    """
    event['ForecastExportJobName'] = FORECAST_EXPORT_JOB_NAME.format(
        project_name=event['ProjectName'],
        date=event['CurrentDate']
    )
    event['ForecastExportJobArn'] = FORECAST_EXPORT_JOB_ARN.format(
        region=event['Region'],
        account=event['AccountID'],
        forecast_name=event['ForecastName'],
        export_job_name=event['ForecastExportJobName']
    )

    try:
        response = forecast_client.describe_forecast_export_job(
            ForecastExportJobArn=event['ForecastExportJobArn']
        )
        logger.info({
            'message': 'forecast_client.describe_forecast_export_job called',
            'response': response
        })
    except forecast_client.exceptions.ResourceNotFoundException:
        logger.info({
            'message': 'creating new forecast export job',
            'forecast_export_job_arn': event['ForecastExportJobArn']
        })
        response = forecast_client.create_forecast_export_job(
            ForecastExportJobName=event['ForecastExportJobName'],
            ForecastArn=event['ForecastArn'],
            Destination={
                'S3Config':
                    {
                        'Path':
                            's3://{bucket}/{folder}/'.format(
                                bucket=environ['S3_BUCKET_NAME'],
                                folder=environ['TGT_S3_FOLDER']
                            ),
                        'RoleArn':
                            environ['FORECAST_EXPORT_JOB_ROLE_ARN']
                    }
            }
        )
        logger.info({
            'message': 'forecast_client.create_forecast_export_job called',
            'response': response
        })

        response = forecast_client.describe_forecast_export_job(
            ForecastExportJobArn=event['ForecastExportJobArn']
        )
        logger.info({
            'message': 'forecast_client.describe_forecast_export_job called',
            'response': response
        })

    # When the resource is in CREATE_PENDING or CREATE_IN_PROGRESS,
    # ResourcePending exception will be thrown and this Lambda function will be retried.
    actions.take_action(response['Status'])

    logger.info({
        'message': 'forecast export job was created',
        'forecast_export_job_arn': event['ForecastExportJobArn']
    })

    return event

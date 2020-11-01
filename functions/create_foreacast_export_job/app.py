from os import environ
import actions
from loader import Loader

FORECAST_EXPORT_JOB_NAME = '{project_name}_{date}'
FORECAST_EXPORT_JOB_ARN = 'arn:aws:forecast:{region}:{account}:forecast-export-job/' \
    '{forecast_name}/{export_job_name}'
LOADER = Loader()


def lambda_handler(event, context):
    print(event)
    status = None
    event['ForecastExportJobName'] = FORECAST_EXPORT_JOB_NAME.format(
        project_name=event['ProjectName'],
        date=event['CurrentDate']
    )
    event['ForecastExportJobArn'] = FORECAST_EXPORT_JOB_ARN.format(
        region=environ['AWS_REGION'],
        account=event['AccountID'],
        forecast_name=event['ForecastName'],
        export_job_name=event['ForecastExportJobName']
    )

    # Creates forecast export job if it does not exist yet. Will trhow an exception
    # while the forecast export job is being created.
    try:
        status = LOADER.forecast_cli.describe_forecast_export_job(
            ForecastExportJobArn=event['ForecastExportJobArn']
        )
    except LOADER.forecast_cli.exceptions.ResourceNotFoundException:
        LOADER.logger.info('Forecast export not found. Creating new export.')
        LOADER.forecast_cli.create_forecast_export_job(
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
        status = LOADER.forecast_cli.describe_forecast_export_job(
            ForecastExportJobArn=event['ForecastExportJobArn']
        )

    actions.take_action(status['Status'])
    return event

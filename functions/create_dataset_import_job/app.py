from os import environ
import actions
from loader import Loader

IMPORT_JOB_NAME = '{dataset_name}_{date}'
IMPORT_JOB_ARN = 'arn:aws:forecast:{region}:{account}:dataset-import-job/{dataset_name}/{import_job_name}'

LOADER = Loader()


def lambda_handler(event, context):
    print(event)
    status = None
    # TODO: Support multiple datasets
    event['DatasetImportJobName'] = IMPORT_JOB_NAME.format(
        dataset_name=event['DatasetName'],
        date=event['CurrentDate']
    )
    event['DatasetImportJobArn'] = IMPORT_JOB_ARN.format(
        region=environ['AWS_REGION'],
        account=event['AccountID'],
        dataset_name=event['DatasetName'],
        import_job_name=event['DatasetImportJobName'],

    )
    try:
        status = LOADER.forecast_cli.describe_dataset_import_job(
            DatasetImportJobArn=event['DatasetImportJobArn']
        )

    except LOADER.forecast_cli.exceptions.ResourceNotFoundException:
        LOADER.logger.info(
            'Dataset import job not found! Will follow to create new job.'
        )

        LOADER.forecast_cli.create_dataset_import_job(
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
        status = LOADER.forecast_cli.describe_dataset_import_job(
            DatasetImportJobArn=event['DatasetImportJobArn']
        )

    actions.take_action(status['Status'])
    return event

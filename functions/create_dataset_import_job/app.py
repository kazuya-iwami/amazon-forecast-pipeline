from os import environ
import actions
from loader import Loader

ARN = 'arn:aws:forecast:{region}:{account}:dataset-import-job/{name}/{name}_{date}'
LOADER = Loader()


def lambda_handler(event, context):
    print(event)
    status = None
    # TODO: Support multiple datasets
    event['DatasetImportJobArn'] = ARN.format(
        account=event['AccountID'],
        date=event['CurrentDate'],
        name=event['Datasets'][0]['DatasetName'],
        region=environ['AWS_REGION']
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
            DatasetImportJobName='{name}_{date}'.format(
                name=event['Datasets'][0]['DatasetName'],
                date=event['CurrentDate']
            ),
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

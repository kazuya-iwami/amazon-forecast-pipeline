from os import environ
from datetime import datetime
from boto3 import client
import actions
from loader import Loader

ACCOUNTID = client('sts').get_caller_identity()['Account']
DATASET_NAME = '{project_name}_{dataset_type}'
DATASET_ARN = 'arn:aws:forecast:{region}:{account}:dataset/{dataset_name}'
LOADER = Loader()


def lambda_handler(event, context):
    print(event)
    event['AccountID'] = ACCOUNTID
    event['CurrentDate'] = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    datasets = event['Datasets']
    status = None
    event['DatasetName'] = DATASET_NAME.format(
        project_name=event['ProjectName'],
        dataset_type=datasets[0]['DatasetType']
    )
    event['DatasetArn'] = DATASET_ARN.format(
        region=environ['AWS_REGION'],
        account=event['AccountID'],
        dataset_name=event['DatasetName']
    )
    try:
        status = LOADER.forecast_cli.describe_dataset(
            DatasetArn=event['DatasetArn']
        )
    except LOADER.forecast_cli.exceptions.ResourceNotFoundException:
        LOADER.logger.info('Dataset not found! Will follow to create dataset.')
        for dataset in datasets:
            LOADER.forecast_cli.create_dataset(
                **dataset,
                DatasetName=event['DatasetName']
            )
        status = LOADER.forecast_cli.describe_dataset(
            DatasetArn=event['DatasetArn']
        )

    actions.take_action(status['Status'])
    return event

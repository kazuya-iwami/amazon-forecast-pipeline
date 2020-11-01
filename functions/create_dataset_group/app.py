from os import environ
import actions
from loader import Loader

DATASET_GROUP_NAME = '{project_name}'
DATASET_GROUP_ARN = 'arn:aws:forecast:{region}:{account}:dataset-group/{dataset_group_name}'
LOADER = Loader()


def lambda_handler(event, context):
    print(event)
    dataset_group = event['DatasetGroup']
    status = None
    event['DatasetGroupName'] = DATASET_GROUP_NAME.format(
        project_name=event['ProjectName']
    )
    event['DatasetGroupArn'] = DATASET_GROUP_ARN.format(
        region=environ['AWS_REGION'],
        account=event['AccountID'],
        dataset_group_name=event['DatasetGroupName'],
    )
    try:
        status = LOADER.forecast_cli.describe_dataset_group(
            DatasetGroupArn=event['DatasetGroupArn']
        )

    except LOADER.forecast_cli.exceptions.ResourceNotFoundException:
        LOADER.logger.info(
            'Dataset Group not found! Will follow to create Dataset Group.'
        )
        LOADER.forecast_cli.create_dataset_group(
            **dataset_group,
            DatasetGroupName=event['DatasetGroupName'],
            DatasetArns=[event['DatasetArn']]
        )

        # TODO: Fix this issue
        #
        # * Create the datasetGroup, since this API call is synchronized,
        # * once it returns 200, we know the corresponding datasetGroup is created successfully.
        # * So we don't need to describe for the datasetGroup status.
        # * Also, refer to: https: // docs.aws.amazon.com/forecast/latest/dg/API_DescribeDatasetGroup.html
        # * datasetGroup doesn't even have the 'Status' attribute.
        # */
        status = LOADER.forecast_cli.describe_dataset_group(
            DatasetGroupArn=event['DatasetGroupArn']
        )

    actions.take_action(status['Status'])
    return event

from os import environ
import boto3
import actions
from loader import Loader

ARN = 'arn:aws:forecast:{region}:{account}:predictor/{name}_{date}'
LOADER = Loader()

cloudwatch_client = boto3.client('cloudwatch')

# Post training accuracy metrics from the previous step (predictor) to CloudWatch


def post_metric(metrics):
    # print(dumps(metrics))
    for metric in metrics['PredictorEvaluationResults']:
        cloudwatch_client.put_metric_data(
            Namespace='FORECAST',
            MetricData=[
                {
                    'Dimensions':
                        [
                            {
                                'Name': 'Algorithm',
                                'Value': metric['AlgorithmArn']
                            }, {
                                'Name': 'Quantile',
                                'Value': str(quantile['Quantile'])
                            }
                        ],
                    'MetricName': 'WQL',
                    'Unit': 'None',
                    'Value': quantile['LossValue']
                } for quantile in metric['TestWindows'][0]['Metrics']
                ['WeightedQuantileLosses']
            ] + [
                {
                    'Dimensions':
                        [
                            {
                                'Name': 'Algorithm',
                                'Value': metric['AlgorithmArn']
                            }
                        ],
                    'MetricName': 'RMSE',
                    'Unit': 'None',
                    'Value': metric['TestWindows'][0]['Metrics']['RMSE']
                }
            ]
        )


def lambda_handler(event, context):
    status = None
    predictor = event['Predictor']
    event['PredictorArn'] = ARN.format(
        account=event['AccountID'],
        date=event['CurrentDate'],
        name=predictor['PredictorName'],
        region=environ['AWS_REGION'],
    )
    try:
        status = LOADER.forecast_cli.describe_predictor(
            PredictorArn=event['PredictorArn']
        )

    except LOADER.forecast_cli.exceptions.ResourceNotFoundException:
        LOADER.logger.info(
            'Predictor not found! Will follow to create new predictor.'
        )
        if 'InputDataConfig' in predictor.keys():
            predictor['InputDataConfig']['DatasetGroupArn'] = event[
                'DatasetGroupArn']
        else:
            predictor['InputDataConfig'] = {
                'DatasetGroupArn': event['DatasetGroupArn']
            }
        LOADER.forecast_cli.create_predictor(**predictor)
        status = LOADER.forecast_cli.describe_predictor(
            PredictorArn=event["PredictorArn"]
        )
    actions.take_action(status['Status'])

    # Completed creating Predictor.
    post_metric(
        LOADER.forecast_cli.get_accuracy_metrics(
            PredictorArn=event['PredictorArn']
        )
    )
    return event

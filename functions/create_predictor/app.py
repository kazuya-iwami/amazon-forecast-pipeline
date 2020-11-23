"""
Creates an Amazon Forecast predictor(ML model).
"""
import boto3
# From Lambda Layers
import actions  # pylint: disable=import-error
from lambda_handler_logger import lambda_handler_logger  # pylint: disable=import-error
from aws_lambda_powertools import Logger  # pylint: disable=import-error

PREDICTOR_NAME = '{project_name}_{date}'
PREDICTOR_ARN = 'arn:aws:forecast:{region}:{account}:predictor/{predictor_name}'

logger = Logger()
forecast_client = boto3.client('forecast')
cloudwatch_client = boto3.client('cloudwatch')


def post_metric(metrics):
    """
    Post training accuracy metrics from the previous step (predictor) to CloudWatch
    """
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


@lambda_handler_logger(logger=logger, lambda_name='create_predictor')
def lambda_handler(event, _):
    """
    Lambda function handler
    """
    event['PredictorName'] = PREDICTOR_NAME.format(
        project_name=event['ProjectName'],
        date=event['CurrentDate']
    )
    event['PredictorArn'] = PREDICTOR_ARN.format(
        region=event['Region'],
        account=event['AccountID'],
        predictor_name=event['PredictorName']
    )
    try:
        response = forecast_client.describe_predictor(
            PredictorArn=event['PredictorArn']
        )
        logger.info({
            'message': 'forecast_client.describe_predictor called',
            'response': response
        })

    except forecast_client.exceptions.ResourceNotFoundException:
        logger.info({
            'message': 'creating new predictor',
            'predictor_arn': event['PredictorArn']
        })
        if 'InputDataConfig' in event['Predictor'].keys():
            event['Predictor']['InputDataConfig']['DatasetGroupArn'] = \
                event['DatasetGroupArn']
        else:
            event['Predictor']['InputDataConfig'] = {
                'DatasetGroupArn': event['DatasetGroupArn']
            }
        response = forecast_client.create_predictor(
            **event['Predictor'],
            PredictorName=event['PredictorName']
        )
        logger.info({
            'message': 'forecast_client.create_predictor called',
            'response': response
        })

        response = forecast_client.describe_predictor(
            PredictorArn=event["PredictorArn"]
        )
        logger.info({
            'message': 'forecast_client.describe_predictor called',
            'response': response
        })

    # When the resource is in CREATE_PENDING or CREATE_IN_PROGRESS,
    # ResourcePending exception will be thrown and this Lambda function will be retried.
    actions.take_action(response['Status'])

    # Completed creating Predictor.
    logger.info({
        'message': 'predictor was created',
        'predictor_arn': event['PredictorArn']
    })

    # Post accuracy information to CloudWatch Metrics
    post_metric(
        forecast_client.get_accuracy_metrics(
            PredictorArn=event['PredictorArn']
        )
    )

    return event

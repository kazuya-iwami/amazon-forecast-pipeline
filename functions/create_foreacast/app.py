from os import environ
from boto3 import client
import actions
from loader import Loader

CLOUDWATCH_CLI = client('cloudwatch')
FORECAST_ARN = 'arn:aws:forecast:{region}:{account}:forecast/{name}_{date}'
FORECAST_EXPORT_JOB_ARN = 'arn:aws:forecast:{region}:{account}:forecast-export-job/' \
    '{name}/{name}_{date}'
LOADER = Loader()


# Post training accuracy metrics from the previous step (predictor) to CloudWatch
def post_metric(metrics):
    # print(dumps(metrics))
    for metric in metrics['PredictorEvaluationResults']:
        CLOUDWATCH_CLI.put_metric_data(
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
    forecast = event['Forecast']
    status = None
    event['ForecastArn'] = FORECAST_ARN.format(
        region=environ['AWS_REGION'],
        account=event['AccountID'],
        name=forecast['ForecastName'],
        date=event['CurrentDate']
    )
    event['ForecastExportJobArn'] = FORECAST_EXPORT_JOB_ARN.format(
        region=environ['AWS_REGION'],
        account=event['AccountID'],
        name=forecast['ForecastName'],
        date=event['CurrentDate']
    )

    # Creates Forecast and export Predictor metrics if Forecast does not exist yet.
    # Will throw an exception while the forecast is being created.
    try:
        actions.take_action(
            LOADER.forecast_cli.describe_forecast(
                ForecastArn=event['ForecastArn']
            )['Status']
        )
    except LOADER.forecast_cli.exceptions.ResourceNotFoundException:
        post_metric(
            LOADER.forecast_cli.get_accuracy_metrics(
                PredictorArn=event['PredictorArn']
            )
        )
        LOADER.logger.info('Forecast not found. Creating new forecast.')
        LOADER.forecast_cli.create_forecast(
            **forecast, PredictorArn=event['PredictorArn']
        )
        actions.take_action(
            LOADER.forecast_cli.describe_forecast(
                ForecastArn=event['ForecastArn']
            )['Status']
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
            ForecastExportJobName='{name}_{date}'.format(
                name=forecast['ForecastName'], date=event['CurrentDate']
            ),
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

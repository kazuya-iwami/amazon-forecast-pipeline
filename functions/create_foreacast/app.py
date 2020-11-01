from os import environ
import actions
from loader import Loader

FORECAST_NAME = '{project_name}_{date}'
FORECAST_ARN = 'arn:aws:forecast:{region}:{account}:forecast/{forecast_name}'
LOADER = Loader()


def lambda_handler(event, context):
    print(event)
    forecast = event['Forecast']
    status = None
    event['ForecastName'] = FORECAST_NAME.format(
        project_name=event['ProjectName'],
        date=event['CurrentDate']
    )
    event['ForecastArn'] = FORECAST_ARN.format(
        region=environ['AWS_REGION'],
        account=event['AccountID'],
        forecast_name=event['ForecastName']
    )

    # Creates Forecast and export Predictor metrics if Forecast does not exist yet.
    # Will throw an exception while the forecast is being created.
    try:
        status = LOADER.forecast_cli.describe_forecast(
            ForecastArn=event['ForecastArn']
        )

    except LOADER.forecast_cli.exceptions.ResourceNotFoundException:
        LOADER.logger.info('Forecast not found. Creating new forecast.')
        LOADER.forecast_cli.create_forecast(
            **forecast,
            ForecastName=event['ForecastName'],
            PredictorArn=event['PredictorArn']
        )
        status = LOADER.forecast_cli.describe_forecast(
            ForecastArn=event['ForecastArn']
        )

    actions.take_action(status['Status'])
    return event

# amazon-forecast-pipeline
ML pipeline sample codes with Amazon Forecast

## About this sample
- Python
- Splitted into two state machines for training and predicting.
- Support three types of Datasets: TARGET_TIME_SERIES, RELATED_TIME_SERIES, ITEM_METADATA

## Deployment
- Create S3 bucket for storing datasets and results of Amazon Forecast
- Edit functions/shared/python/params.json. This is a setting file for Amazon Forecast.
- sam build
- sam deploy --stack_name forecast-my-dataset --capabilities "CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND" --parameter-overrides S3BucketName='your-s3-bucket-name'



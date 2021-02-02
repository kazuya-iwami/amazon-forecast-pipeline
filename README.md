# amazon-forecast-pipeline
ML pipeline sample codes with Amazon Forecast

## About this sample
- Python-based
- Splitted into two state machines for training and predicting.
- Support three types of Datasets: TARGET_TIME_SERIES, RELATED_TIME_SERIES, ITEM_METADATA
- Similar projects
  - https://github.com/aws-samples/amazon-automated-forecast
  - https://github.com/awslabs/improving-forecast-accuracy-with-machine-learning
  - https://github.com/aws-samples/amazon-forecast-samples/tree/master/ml_ops/visualization_blog

## Architecture
![update_model_flow](https://github.com/kazuya-iwami/amazon-forecast-pipeline/blob/master/docs/images/update_model_flow.jpg "update_model_flow")

![update_forecast_flow](https://github.com/kazuya-iwami/amazon-forecast-pipeline/blob/master/docs/images/update_forecast_flow.jpg "update_forecast_flow")

## Usage
- Create S3 bucket for storing datasets and results of Amazon Forecast
- Put dataset files on S3 backet (See `Setting > S3 Bucket`)
- Edit functions/shared/python/params.json. This is a setting file for Amazon Forecast.
- ```sam build```
- ```sam deploy --stack-name forecast-pipeline --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND --parameter-overrides S3BucketName=<your-s3-bucket-name>, EmailAddress=<your-email-address> ```

## Setting
### S3 bucket
Sample datasets are stored in `/samples`. You can put the three dataset files to the following S3 path:
```
  your-s3-bucket
    /source
        /target_time_series.csv
        /related_time_series.csv (optional)
        /item_metadata.csv (optional)
```

Results of forecast are exported to the following S3 path:
```
  your-s3-bucket
    /target
        /project_name_timestamp_part0.csv
```


## Note
- Create one stack per one AWS account to avoid resouce limit of Amazon Forecast.
- For trouble shooting, you can use CloudWatch Logs Insights
```
fields @timestamp, lambda_name, message.message
| filter service = 'project_name' and trace_id = 'trace_id'
| sort @timestamp
| limit 300
```

```
fields @timestamp, trace_id, lambda_name, message.message
| filter service = 'project_name' and level = 'ERROR'
| sort @timestamp
| limit 300
```


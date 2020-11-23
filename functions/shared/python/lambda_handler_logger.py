from datetime import datetime
from os import environ
import boto3


def lambda_handler_logger(logger, lambda_name):
    """
    Setup logger for lambda handler.
    - initialize
    - setup logger
    - convert exception logs to JSON
    - add start and end log messages
    """
    def decorator(func):
        def wrapper(event, context):
            try:
                if 'ProjectName' not in event:
                    # This is the first lambda_handler() in a state macine flow.
                    # Initialize params
                    event['ProjectName'] = environ['STACK_NAME'].replace(
                        '-', '_')
                    event['AccountID'] = boto3.client(
                        'sts').get_caller_identity()['Account']
                    event['Region'] = environ['AWS_REGION']

                    # Replace hyphen of stack_name to underscore because some resource names do not support hyphen.
                    event['CurrentDate'] = datetime.now().strftime(
                        "%Y_%m_%d_%H_%M_%S")
                    event['TraceId'] = event['StateMachineName'] + \
                        '_' + event['CurrentDate']

                # Setup logger
                logger.structure_logs(
                    append=False, lambda_name=lambda_name, trace_id=event['TraceId'])
                logger.info(
                    {'message': 'starting lambda_handler()', 'event': event, 'environ': environ, 'context': context})

                result = func(event, context)

                logger.info(
                    {'message': 'finished lambda_handler()', 'result': result})
                return result

            except Exception as e:
                if e.__class__.__name__ == 'ResourcePending':
                    # This is not an unexpected excepton.
                    logger.info({
                        'message': 'ResourcePending exception found. Step Functions may retry this function.'
                    })
                else:
                    logger.exception({
                        'message': 'unexpected exception found: ' + repr(e)
                    })

                raise e
        return wrapper
    return decorator

from datetime import datetime
from os import environ
import boto3


def init_basic_params():
    """
    Initialize params
    """
    def decorator(func):
        def wrapper(event, context):
            # Replace hyphen of stack_name to underscore because some resource names do not support hyphen.
            event['ProjectName'] = environ['STACK_NAME'].replace(
                '-', '_')
            event['AccountID'] = boto3.client(
                'sts').get_caller_identity()['Account']
            event['Region'] = environ['AWS_REGION']

            event['TriggeredAt'] = datetime.now().strftime(
                "%Y_%m_%d_%H_%M_%S")
            event['TraceId'] = event['StateMachineName'] + \
                '_' + event['TriggeredAt']

            func(event, context)

        return wrapper
    return decorator

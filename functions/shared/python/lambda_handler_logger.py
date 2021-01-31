
from os import environ


def lambda_handler_logger(logger, lambda_name):
    """
    Setup logger for lambda handler.
    - setup logger
    - convert exception logs to JSON
    - add starting and ending log messages
    """
    def decorator(func):
        def wrapper(event, context):
            try:
                if 'TraceId' not in event:
                    # This is the first lambda_handler() in a state macine flow.
                    event['TraceId'] = 'INITIALIZING'

                # Setup logger
                logger.structure_logs(
                    append=True, lambda_name=lambda_name, trace_id=event['TraceId'])
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
                        'message': 'an exception found: ' + repr(e)
                    })

                raise e
        return wrapper
    return decorator


def lambda_handler(event, context):
    """Sample Code

    Parameters
    ----------
    event: dict, required
        Input event to the Lambda function

    context: object, required
        Lambda Context runtime methods and attributes

    Returns
    ------
        dict: sample data
    """
    print("Called")
    sample_data = {"message": "test"}
    return sample_data

import json
import glob


def load_params():
    print(glob.glob("/opt/*/*.*"))
    with open('/opt/python/params.json') as f:
        params = json.load(f)
        return params

"""Cloudformation macro for transforming templates to use different CFN configuration blocks on a per-environment basis
More powerful than using Mappings/FindInMap funciton as entire config blocks can be deteremined based on the environment
"""
import json
import logging
import pprint

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Name of your CloudFormation parameter that denotes the environment name. This is required to be added to your templates
ENV_PARAMETER_NAME = "EnvironmentName"

# Keys we don't want to crawl, probably won't make a huge impact on performance if we didn't ignore these
IGNORED_KEYS = ["Ref", "Metadata", "Parameters", "Fn::GetAtt"]

def find_macro(data, path=None):
    """Recursively crawl through the template looking for the macro using python generators"""
    # Array to keep track of the key path that needs to be transformed later
    if not path:
        path = []
    for k in data.copy().keys():
        if k in IGNORED_KEYS:
            continue
        temp_path = path[:]
        temp_path.append(k)
        if k == 'AdvancedMapping':
            # Macro should not be nested so no recursion here.  Once macro is found, the parent path will be completely replaced with whatever is in the macro
            yield temp_path,data[k]
        elif isinstance(data[k], dict):
            # If value is a dictionaly, crawl deeper
            for r in find_macro(data[k], temp_path):
                yield r
        else:
            continue

def transform(transform_data, envtype_value):
    """Return the sub dataset defined in the template according to the passed in EnvType variable"""
    if envtype_value in transform_data.keys():
        # If the EnvType value is found within the macro block, only return that dictionary (rest will be deleted)
        return transform_data[envtype_value]
    elif "allOthers" in transform_data.keys():
        # If EnvType value is not found, but an allOthers block is found, return that.
        return transform_data["allOthers"]
    else:
        # If none of the above, the particular key with the macro block in it will be deleted from the template
        return None
    
def handler(event, context):
    """Default handler"""
    logger.info("Recieved: " + json.dumps(event))
    response_fragment = event["fragment"].copy()
    try:
        environment_name = event["templateParameterValues"][ENV_PARAMETER_NAME]
        logger.info("Environment name: " + environment_name)
    except KeyError:
        error_message = "Expecting there to be a paramater named: " + ENV_PARAMETER_NAME + ", but did not find one.  Please specify that parameter in your template, or update the ENV_PARAMETER_NAME constant in app.py"
        logger.error(error_message)
        return {
            'requestId': event['requestId'],
            'status': 'fail',
            'errorMessage': error_message
        }
    for transform_path,transform_data in find_macro(event["fragment"]):
        key_to_transform = response_fragment
        # Reference the second to last value in the path in order to replace the value of the key parent to the macro (and not the macro key itself)
        last_path = transform_path[-2]
        # Rebuild the reference to the path in order to edit it. -2 as the last path is the macro itself, and 2nd to last path is stored in the last_path variable above
        for path in transform_path[:-2]:
            key_to_transform = key_to_transform[path]
        logger.info("Macro found at: " + str(transform_path) + json.dumps(key_to_transform[last_path]['AdvancedMapping']))
        # Call the transform function to pick which environment's configuration to put in the template (the others will get deleted)
        snippet = transform(transform_data, environment_name)
        if snippet is None:
            logger.info("No match found for " + environment_name)
            del key_to_transform[last_path]['AdvancedMapping']
        else:
            logger.info("Updating to: " + json.dumps(snippet))
            key_to_transform[last_path].update(snippet)
            del key_to_transform[last_path]['AdvancedMapping']
    logger.info("Transformed template: " + json.dumps(response_fragment))
    return {
        'requestId': event['requestId'],
        'status': 'success',
        'fragment': response_fragment
    }        

# Used for local testing, ignore
if __name__ == "__main__":
    with open('test_event.json', 'r') as file:
        event_json = json.loads(file.read())
    result = handler(event_json, {})
    pprint.pprint(result['fragment'])
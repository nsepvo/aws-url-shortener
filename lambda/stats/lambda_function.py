import json
import os
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

def lambda_handler(event, context):
    code = event["pathParameters"]["code"]

    try:
        response = table.get_item(Key={"code": code})
    except ClientError as e:
        print(e.response["Error"])
        return {"statusCode": 500, "body": json.dumps({"error": "Database error"})}

    item = response.get("Item")
    if not item:
        return {"statusCode": 404, "body": json.dumps({"error": "Short URL not found"})}

    # Default clicks to 0 in case the item was created before
    # click tracking was added — avoids a KeyError on older items
    return {
        "statusCode": 200,
        "body": json.dumps({
            "code": code,
            "originalUrl": item["originalUrl"],
            "clicks": int(item.get("clicks", 0)),
            "createdAt": item["createdAt"],
        })
    }

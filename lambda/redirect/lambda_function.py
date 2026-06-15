import json
import os
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

def lambda_handler(event, context):
    code = event["pathParameters"]["code"]
    now = int(datetime.now(timezone.utc).timestamp())

    # Use update_item instead of get_item so we can increment the click
    # counter and fetch the item in a single atomic DynamoDB operation.
    # ADD is atomic — safe for concurrent clicks without losing counts.
    try:
        response = table.update_item(
            Key={"code": code},
            UpdateExpression="ADD clicks :inc",
            # Check the item exists and hasn't expired — DynamoDB TTL deletion
            # isn't instant so we enforce expiry manually here
            ConditionExpression="attribute_exists(code) AND (#ttl > :now OR attribute_not_exists(#ttl))",
            ExpressionAttributeNames={"#ttl": "ttl"},
            ExpressionAttributeValues={":inc": 1, ":now": now},
            ReturnValues="ALL_NEW",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {"statusCode": 404, "body": json.dumps({"error": "Short URL not found or expired"})}
        return {"statusCode": 500, "body": json.dumps({"error": "Database error"})}

    item = response["Attributes"]

    # 301 permanently redirects the browser — the Location header tells
    # the browser where to go and it follows it automatically
    return {
        "statusCode": 301,
        "headers": {"Location": item["originalUrl"]},
        "body": ""
    }

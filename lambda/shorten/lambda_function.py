import json
import os
import random
import string
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

def generate_code(length=6):
    # 6 characters from a-z, A-Z, 0-9 gives us ~56 billion possible codes
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))

def is_valid_url(url):
    # Make sure the URL has a valid scheme and domain before storing it
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

def lambda_handler(event, context):
    body = json.loads(event["body"])
    original_url = body.get("url")
    alias = body.get("alias")

    if not original_url:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing url"})}

    if not is_valid_url(original_url):
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid URL. Must start with http:// or https://"})}

    # Only allow alphanumeric aliases to avoid URL routing issues
    if alias and not alias.isalnum():
        return {"statusCode": 400, "body": json.dumps({"error": "Alias must be alphanumeric only"})}

    # Set expiry to 30 days from now — stored as Unix timestamp because
    # that's what DynamoDB TTL requires for automatic deletion
    expires_at = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())

    if alias:
        # User provided a custom alias — try to claim it once
        # If it's already taken we return a 409 rather than retrying with a different code
        try:
            table.put_item(
                Item={
                    "code": alias,
                    "originalUrl": original_url,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "ttl": expires_at,
                },
                ConditionExpression="attribute_not_exists(code)",
            )
            code = alias
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return {"statusCode": 409, "body": json.dumps({"error": "Alias already taken"})}
            raise
    else:
        # No alias provided — generate a random code
        # Retry up to 5 times in case of a collision (extremely rare with 56B possibilities)
        for _ in range(5):
            code = generate_code()
            try:
                table.put_item(
                    Item={
                        "code": code,
                        "originalUrl": original_url,
                        "createdAt": datetime.now(timezone.utc).isoformat(),
                        "ttl": expires_at,
                    },
                    # Only write if this code doesn't already exist — prevents
                    # overwriting an existing URL and avoids a read-then-write race condition
                    ConditionExpression="attribute_not_exists(code)",
                )
                break
            except ClientError as e:
                if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                    continue
                raise

    domain = event["requestContext"]["domainName"]
    short_url = f"https://{domain}/{code}"
    return {"statusCode": 200, "body": json.dumps({"shortUrl": short_url, "code": code})}

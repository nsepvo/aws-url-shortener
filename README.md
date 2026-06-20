## AWS Serverless URL Shortener

A fully serverless URL shortener built on AWS, designed to convert long URLs into short, shareable links that fit comfortably in small spaces and on mobile screens. Built primarily to deepen understanding of DynamoDB and multi-service AWS architecture, with a focus on data integrity, atomic operations, and edge delivery.

## Live Demo

https://staging.d3w1w0m6iehn9k.amplifyapp.com/

## Architecture

![Architecture Diagram](architecture.png)

## AWS Services Used

- AWS Amplify – Frontend hosting with automatic CI/CD on push
- Amazon CloudFront – Global edge delivery and HTTPS termination
- Amazon API Gateway – Public-facing REST API with throttling and burst rate limits
- AWS Lambda – Backend logic across three functions (Python)
- Amazon DynamoDB – Short code and URL storage
- Amazon S3 – Static asset storage

## Request Flow 
### Creating a Short URL

1. The user submits a long URL and an optional custom alias via the frontend
2. API Gateway forwards the request to Lambda
3. Lambda checks DynamoDB for an existing alias — if taken, the user is prompted to choose another
4. Lambda performs a conditional write, only inserting the item if the short code does not already exist
5. The short URL is returned to the frontend

### Request Flow - Redirect

1. The user visits a short URL
2. CloudFront forwards the request to API Gateway, which triggers the redirect Lambda
3. Lambda retrieves the item from DynamoDB and manually checks whether it has expired
4. If valid, Lambda returns a 302 redirect to the original URL and atomically increments the click counter
5. If expired or not found, Lambda returns an appropriate error response

## Design Decisions

- DynamoDB over RDS - short codes map directly to long URLs, making a key-value store a natural fit. DynamoDB's partition key design mirrors this structure exactly, and its atomic operation support is essential for safe concurrent writes
- Conditional writes for duplicate prevention - rather than reading a short code, checking for duplicates in Python, and then writing, DynamoDB's conditional write performs this as a single atomic operation. This closes the gap where two simultaneous requests could generate the same code and overwrite each other silently
- 302 over 301 redirects - a 301 is cached permanently by the browser, meaning clicks would bypass Lambda entirely, breaking analytics and expiry enforcement. A 302 ensures every click flows through the redirect function
- Manual TTL expiry check in Lambda - DynamoDB's built-in TTL can lag up to 48 hours before physically deleting expired items. Without a manual timestamp check in Lambda, expired links could still redirect successfully during that window
- CloudFront for edge delivery - for a URL shortener, redirect speed matters. CloudFront handles requests at the nearest edge location globally, reducing latency and providing DDoS protection and HTTPS termination without additional configuration
- Optional custom alias - users can define their own 6-character slug. If the alias already exists in DynamoDB, they are prompted to choose another. If left blank, a random code is generated automatically
- API Gateway throttling - burst rate limits are applied at the API layer to prevent abuse and protect DynamoDB from request floods

## Key Learnings

- DynamoDB atomic operations close race condition gaps - early on, the assumption was that Lambda would read an item, process it, and write back. Understanding that DynamoDB can perform conditional reads and writes as a single indivisible operation was a significant shift. It moves the integrity check into the database layer where it belongs
- DynamoDB TTL is not instant - TTL marks items for deletion when their timestamp passes, but physical removal can lag by up to 48 hours. A manual expiry check in the redirect Lambda is necessary to prevent expired links from remaining active during that window
- Environment variables must be exact across every function - with three separate Lambda functions sharing configuration like table names and region, a single typo in an environment variable causes silent failures that are harder to trace than code errors. Consistent naming conventions matter more than expected
- Unix epoch time is used for a reason - DynamoDB TTL requires timestamps in epoch format. Understanding why — that epoch time is a single universal integer independent of timezone or locale — clarified why AWS and large-scale systems default to it over human-readable formats
- Reading DynamoDB output correctly takes adjustment - early errors came from misreading the structure of DynamoDB responses rather than misconfiguring the table. Once the response format was understood, parsing became straightforward and predictable

## What I Would Do Next

- Authentication via Amazon Cognito - allow users to create accounts, manage their own links, and view personal analytics
- Click analytics dashboard - surface click count data over time rather than just a running total, using the existing counter as a foundation
- QR code generation - automatically generate a scannable QR code for every short URL, since short links and QR codes serve the same use case
- URL validation and blocklisting - reject known malicious or inappropriate domains before storing them, and validate that submitted URLs are well-formed
- Enhanced rate limiting - supplement API Gateway throttling with per-IP controls to prevent a single user from flooding the table with short codes
- Custom domain - replace the CloudFront-generated domain with a short custom domain to make the shortened URLs genuinely compact


## Contact

Open to internship and graduate opportunities in software engineering and cloud computing.

- Email: nevenspooner03@gmail.com
- LinkedIn: https://www.linkedin.com/in/neven-spooner/

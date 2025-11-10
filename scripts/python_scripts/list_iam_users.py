import boto3

# 1. Create an IAM client
iam = boto3.client('iam')

# 2. Call the list_users API
response = iam.list_users()

# 3. Print each user's details
print("IAM Users in this AWS account:\n")
for user in response['Users']:
    print(f"User Name: {user['UserName']}")
    print(f"User ID: {user['UserId']}")
    print(f"ARN: {user['Arn']}")
    print(f"Created On: {user['CreateDate']}")
    print("-" * 40)

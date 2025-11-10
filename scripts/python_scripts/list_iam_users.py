import boto3
from datetime import datetime, timezone

# Create IAM client
iam = boto3.client('iam')

def get_user_details(user):
    """Return extended details for a single IAM user."""
    username = user['UserName']
    user_info = {
        'UserName': username,
        'CreatedOn': user['CreateDate'].strftime("%Y-%m-%d %H:%M:%S"),
        'ConsoleLogin': False,
        'CLIEnabled': False,
        'LastAccessed': "N/A",
        'Type': "Unknown"
    }

    # ---- Check console access (login profile exists?) ----
    try:
        iam.get_login_profile(UserName=username)
        user_info['ConsoleLogin'] = True
    except iam.exceptions.NoSuchEntityException:
        user_info['ConsoleLogin'] = False

    # ---- Check access keys (CLI/API access) ----
    keys = iam.list_access_keys(UserName=username)['AccessKeyMetadata']
    if keys:
        user_info['CLIEnabled'] = True
        # find the most recent access among keys
        last_used_times = []
        for k in keys:
            last_used = iam.get_access_key_last_used(AccessKeyId=k['AccessKeyId'])
            if 'LastUsedDate' in last_used['AccessKeyLastUsed']:
                last_used_times.append(last_used['AccessKeyLastUsed']['LastUsedDate'])
        if last_used_times:
            latest = max(last_used_times)
            user_info['LastAccessed'] = latest.strftime("%Y-%m-%d %H:%M:%S")

    # ---- Categorize ----
    if user_info['ConsoleLogin']:
        user_info['Type'] = "LOCAL_USER"
    elif user_info['CLIEnabled']:
        user_info['Type'] = "SERVICE_ACCOUNT"

    return user_info


def main():
    # List all users (handle pagination)
    paginator = iam.get_paginator('list_users')
    all_users = []
    for page in paginator.paginate():
        all_users.extend(page['Users'])

    print(f"\n{'UserName':<20} {'ConsoleLogin':<15} {'CLIEnabled':<12} {'LastAccessed':<22} {'Type':<18} {'CreatedOn'}")
    print("-" * 100)

    for user in all_users:
        details = get_user_details(user)
        print(f"{details['UserName']:<20} {str(details['ConsoleLogin']):<15} "
              f"{str(details['CLIEnabled']):<12} {details['LastAccessed']:<22} "
              f"{details['Type']:<18} {details['CreatedOn']}")
    print("-" * 100)
    print(f"Total users: {len(all_users)}")


if __name__ == "__main__":
    main()

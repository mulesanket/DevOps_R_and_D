import boto3
from datetime import datetime, timezone
from tabulate import tabulate   # <-- for neat table output

# Create IAM client
iam = boto3.client('iam')


def days_since(date):
    """Return number of days since a given date."""
    if not date:
        return None
    return (datetime.now(timezone.utc) - date).days


def get_user_details(user):
    username = user['UserName']
    user_path = user['Path']
    details = {
        'User': username,
        'UserType': 'Unknown',
        'TypeOfAccess': 'None',
        'Permissions': '',
        'LastLoginDays': None,
        'EligibleToRemove': 'No'
    }

    # ---- Determine user type from Path ----
    if user_path.strip("/") == "service":
        details['UserType'] = 'Service'
    else:
        details['UserType'] = 'Local'

    # ---- Check console access ----
    try:
        iam.get_login_profile(UserName=username)
        details['TypeOfAccess'] = 'Console'
    except iam.exceptions.NoSuchEntityException:
        pass  # no console login

    # ---- Check CLI access (access keys) ----
    keys = iam.list_access_keys(UserName=username)['AccessKeyMetadata']
    if keys:
        if details['TypeOfAccess'] == 'Console':
            details['TypeOfAccess'] = 'Both'
        else:
            details['TypeOfAccess'] = 'CLI'

    # ---- Permissions (attached policies + groups) ----
    policies = []
    attached_policies = iam.list_attached_user_policies(UserName=username)['AttachedPolicies']
    for p in attached_policies:
        policies.append(p['PolicyName'])
    groups = iam.list_groups_for_user(UserName=username)['Groups']
    for g in groups:
        policies.append(f"Group:{g['GroupName']}")
    details['Permissions'] = ", ".join(policies) if policies else "None"

    # ---- Last login / API key usage ----
    login_date = user.get('PasswordLastUsed')
    key_used_dates = []
    for k in keys:
        info = iam.get_access_key_last_used(AccessKeyId=k['AccessKeyId'])
        last_used = info['AccessKeyLastUsed'].get('LastUsedDate')
        if last_used:
            key_used_dates.append(last_used)

    all_dates = [d for d in [login_date, *key_used_dates] if d]
    if all_dates:
        most_recent = max(all_dates)
        details['LastLoginDays'] = days_since(most_recent)
    else:
        details['LastLoginDays'] = None

    # ---- Eligibility for removal ----
    if (
        (not login_date or days_since(login_date) >= 90)
        and (not key_used_dates or all(days_since(d) >= 90 for d in key_used_dates))
    ):
        details['EligibleToRemove'] = 'Yes'

    return details


def main():
    paginator = iam.get_paginator('list_users')
    all_users = []

    for page in paginator.paginate():
        for user in page['Users']:
            all_users.append(get_user_details(user))

    # ---- Prepare table data ----
    headers = ["User", "UserType", "TypeOfAccess", "Permissions", "LastLoginDays", "EligibleToRemove"]
    rows = [
        [
            u['User'],
            u['UserType'],
            u['TypeOfAccess'],
            u['Permissions'],
            u['LastLoginDays'],
            u['EligibleToRemove'],
        ]
        for u in all_users
    ]

    # ---- Print pretty table ----
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print(f"\nTotal users: {len(all_users)}")


if __name__ == "__main__":
    main()

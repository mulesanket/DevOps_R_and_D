import boto3
import pandas as pd
from datetime import datetime, timezone
from tabulate import tabulate
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font
from openpyxl import load_workbook

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

    # ---- Eligibility for removal ----
    if (
        (not login_date or days_since(login_date) >= 90)
        and (not key_used_dates or all(days_since(d) >= 90 for d in key_used_dates))
    ):
        details['EligibleToRemove'] = 'Yes'

    return details


def format_excel(file_path):
    """Apply basic formatting to Excel (bold headers, auto column width)."""
    wb = load_workbook(file_path)
    ws = wb.active

    # Bold header row
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Auto-adjust column width
    for col in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        adjusted_width = (max_length + 3)
        ws.column_dimensions[col_letter].width = adjusted_width

    wb.save(file_path)


def main():
    paginator = iam.get_paginator('list_users')
    all_users = []

    print("Fetching IAM users... Please wait.\n")

    for page in paginator.paginate():
        for user in page['Users']:
            all_users.append(get_user_details(user))

    # ---- Print formatted table ----
    headers = ["User", "UserType", "TypeOfAccess", "Permissions", "LastLoginDays", "EligibleToRemove"]
    rows = [[u[h] for h in headers] for u in all_users]
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print(f"\nTotal users: {len(all_users)}")

    # ---- Generate Excel file ----
    df = pd.DataFrame(all_users)
    output_path = "/home/ubuntu/DevOps_R_and_D/scripts/python_scripts/iam_users_report.xlsx"
    df.to_excel(output_path, index=False)
    format_excel(output_path)

    print(f"\n✅ Excel report saved at: {output_path}")


if __name__ == "__main__":
    main()

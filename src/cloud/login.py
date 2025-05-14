import boto3
import botocore
import subprocess
from azure.identity import DeviceCodeCredential
from azure.mgmt.resource import SubscriptionClient

def one_click_aws_login(profile_name="bio-cloud"):
    """
    Checks for a valid AWS SSO session. If not present, it triggers a login.
    Returns a boto3 session or None on failure.
    """
    try:
        session = boto3.Session(profile_name=profile_name)
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        return session, f"✅ Logged in as: {identity['Arn']}"
    except botocore.exceptions.BotoCoreError:
        subprocess.run(["aws", "sso", "login", "--profile", profile_name])
        # Retry after login
        try:
            session = boto3.Session(profile_name=profile_name)
            sts = session.client("sts")
            identity = sts.get_caller_identity()
            return session, f"✅ Logged in as: {identity['Arn']}"
        except Exception as e:
            return None, f"❌ Login failed: {e}"


def one_click_azure_login():
    """
    Performs one-click login to Azure using Device Code flow.
    Returns: credential object, login message, and subscription info if successful.
    """
    try:
        # Authenticate using Device Code Flow (user logs in via browser)
        credential = DeviceCodeCredential(
            client_id="04b07795-8ddb-461a-bbee-02f9e1bf7b46",  # Public client (Azure CLI)
        )

        # Validate authentication by listing subscriptions
        sub_client = SubscriptionClient(credential)
        subscriptions = list(sub_client.subscriptions.list())

        if subscriptions:
            sub_names = [sub.display_name for sub in subscriptions]
            return credential, f"✅ Logged in to Azure. Subscriptions: {', '.join(sub_names)}"
        else:
            return None, "⚠️ Login succeeded but no subscriptions found."

    except Exception as e:
        return None, f"❌ Azure login failed: {str(e)}"



# Test
if __name__ == "__main__":
    session = one_click_aws_login()
    # Now use session.resource or session.client to access any service
    s3 = session.client("s3")
    buckets = s3.list_buckets()
    print("📦 Available Buckets:", [b['Name'] for b in buckets['Buckets']])

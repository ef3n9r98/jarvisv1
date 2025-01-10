import os
from pathlib import Path
from dotenv import load_dotenv
import slack

# Load environment variables
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Initialize Slack client
client = slack.WebClient(token=os.environ['SLACK_TOKEN'])

def fetch_users_list():
    """
    Fetch the list of all users in the workspace.
    Returns:
        dict: A dictionary with user IDs as keys and real names (or display names) as values.
    """
    try:
        response = client.users_list()
        if response.get("ok"):
            users = response.get("members", [])
            user_dict = {}
            for user in users:
                user_id = user.get("id")
                real_name = user.get("real_name") or user["profile"].get("display_name")
                user_dict[user_id] = real_name
            return user_dict
        else:
            print(f"Error fetching users: {response.get('error')}")
            return {}
    except Exception as e:
        print(f"Exception occurred: {e}")
        return {}

def get_real_name(user_id, users_dict):
    """
    Retrieve the real name of a user by their Slack user ID.

    Parameters:
        user_id (str): The Slack user ID.
        users_dict (dict): A dictionary mapping user IDs to names (real or display names).

    Returns:
        str: The real name of the user, or "Unknown User" if the ID is not found.
    """
    return users_dict.get(user_id, "Unknown User")


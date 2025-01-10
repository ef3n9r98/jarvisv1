import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

NOTION_API_URL = "https://api.notion.com/v1/pages"

def convert_markdown_to_rich_text(markdown_text):
    """Convert Markdown links to Notion rich text format with hyperlinks."""
    import re

    # Match Markdown links ([text](url))
    link_pattern = r"\[(.*?)\]\((.*?)\)"
    parts = re.split(link_pattern, markdown_text)

    # Create rich text blocks
    rich_text = []
    i = 0
    while i < len(parts):
        if i % 3 == 0:  # Plain text (not part of a link)
            if parts[i].strip():  # Ignore empty strings
                rich_text.append({
                    "type": "text",
                    "text": {"content": parts[i]},
                    "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}
                })
        elif i % 3 == 1:  # Link text
            link_text = parts[i]
        elif i % 3 == 2:  # URL
            rich_text.append({
                "type": "text",
                "text": {"content": link_text, "link": {"url": parts[i]}},
                "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}
            })
        i += 1

    return rich_text


def create_notion_page(title, description, status_id, reported_by_name):
    """
    Creates a new page in the Notion database.

    Args:
        title (str): Title of the Notion page.
        description (str): Description to be added as a paragraph in the Notion page.
        status_id (str): Status ID from the Notion database.
        reported_by_name (str): Name of the person who reported the issue.

    Returns:
        str: URL of the created Notion page if successful, None otherwise.
    """
    # Construct payload
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "Status": {"status": {"id": status_id}},
            "Reported By": {"rich_text": [{"text": {"content": reported_by_name}}]},  # Add Reported By
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": convert_markdown_to_rich_text(description)
                    # Convert Markdown to Notion-compatible rich text
                },
            }
        ],
    }

    # Define headers
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    # Make POST request to Notion API
    try:
        response = requests.post(NOTION_API_URL, headers=headers, json=payload)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        response_data = response.json()

        # Extract page URL
        page_id = response_data.get("id")
        if page_id:
            notion_url = f"https://www.notion.so/{page_id.replace('-', '')}"
            print(f"New Notion page created: {notion_url}")
            return notion_url
        else:
            print("Failed to retrieve page ID from Notion response.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

'''
def create_notion_page(title, description, status_id):
    """
    Creates a new page in the Notion database.

    Args:
        title (str): Title of the Notion page.
        description (str): Description to be added as a paragraph in the Notion page.
        status_id (str): Status ID from the Notion database.

    Returns:
        str: URL of the created Notion page if successful, None otherwise.
    """
    # Construct payload
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "Status": {"status": {"id": status_id}}
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": description}}]
                }
            }
        ]
    }

    # Define headers
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # Make POST request to Notion API
    try:
        response = requests.post(NOTION_API_URL, headers=headers, json=payload)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        response_data = response.json()

        # Extract page URL
        page_id = response_data.get("id")
        if page_id:
            notion_url = f"https://www.notion.so/{page_id.replace('-', '')}"
            print(f"New Notion page created: {notion_url}")
            return notion_url
        else:
            print("Failed to retrieve page ID from Notion response.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
'''
import os
import json
import logging
import datetime

import yaml
import requests

from utilities.state import load

logger = logging.getLogger(__name__)

def send_google_message(webhook: str, resource: dict, state: dict, workflow_status: bool):
    """
    Sends a report of the workflow result to a google chat room
    Workflow status. One of: Succeeded, Failed, Error
    """
    message = {
        "cardsV2": [
            {
                "cardId": "card_one",
                "card": {
                    "header": {
                        "title": f"Provisioning AXIS '{resource['metadata']['name']}' {workflow_status}!",
                        "subtitle": f"{datetime.datetime.utcnow().isoformat()} UTC"
                    },
                    "sections": [
                        {
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": f"{yaml.safe_dump(resource)}"
                                    }
                                },
                            ]
                        }
                    ]
                }
            }
        ]
    }

    if state.get('error') is not None:
        message['cardsV2'][0]['card']['sections'].append({
            "widgets": [
                {
                    "textParagraph": {
                        "text": state["error"]
                    }
                },
            ]
        })

    requests.post(
        webhook,
        data=json.dumps(message),
        headers={"Content-Type": "application/json; charset=UTF-8"}
    )


def send_slack_message(webhook: str, resource: dict, state: dict, workflow_status: bool):
    """
    Sends a report of the workflow result to a Slack channel
    Workflow status. One of: Succeeded, Failed, Error
    """
    message = {
        "icon_emoji": ":robot_face:",
        "username": "Provisioning Bot",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"""
Provisioning AXIS '{resource['metadata']['name']}' {workflow_status}!
{datetime.datetime.utcnow().isoformat()} UTC
                    """
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"""
                        ```
{yaml.safe_dump(resource)}
                        ```
                    """
                }
            }
        ]
    }

    if state.get('error') is not None:
        message['blocks'].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": state["error"]
            }
        }) 
    
    requests.post(
        webhook,
        data=json.dumps(message),
        headers={"Content-Type": "application/json; charset=UTF-8"}
    )


def run(resource: dict):
    state = load()

    # send slack message
    send_slack_message(
        webhook = os.getenv("SLACK_WEBHOOK"),
        resource = resource,
        state = state,
        workflow_status = os.getenv("WORKFLOW_STATUS")
    )

    # send google chat message
    send_google_message(
        webhook = os.getenv("GOOGLE_WEBHOOK"),
        resource = resource,
        state = state,
        workflow_status = os.getenv("WORKFLOW_STATUS")
    )

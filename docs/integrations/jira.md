# Jira

This repository does not connect to Jira by itself, and it does not ship tokens. Two different Cursor products can read the same issues once you connect them. They are not the same integration.

## A. Atlassian Rovo MCP

Use this when an agent in Cursor should search or read Jira. Install the official Atlassian MCP server from Cursor Settings → MCP, and sign in with your own Atlassian account. The agent can then look up issues you can already see. Meridian Flow does not proxy that connection.

If you do not have a Jira site, skip this. The issue text is in `docs/product/tickets/` and the agent can read those files directly.

## B. Cursor native Jira → Cloud Agent

Use this when you want to assign a Jira issue to Cursor or mention `@Cursor` so a Cloud Agent starts. That connection is configured in the Cursor dashboard (Integrations → Jira), not in this repo. It requires a Jira admin to install the Cursor app on the site, and a git host the Cloud Agent can push to.

## Issue map

| Key | Workflow |
| --- | --- |
| MGB-142 | Local agent, Plan mode, then implement resolution guidance |
| MGB-143 | Browser refinement of that guidance, after MGB-142 |
| MGB-318 | Cloud Agent, settlement discrepancy investigation |
| MGB-407 | Pull-request review on `demo/mgb-407-cutoff-regression` |
| MGB-502 | Incident investigation / automation |

`docs/product/jira-import.csv` is a CSV you can import into a Jira project with key `MGB` if you want the issues in a real site. Importing it is your action. Until then, point the agent at the markdown files.

## Fallback

"Read `docs/product/tickets/MGB-142.md`, summarise it, and plan the change. Do not implement until I approve."

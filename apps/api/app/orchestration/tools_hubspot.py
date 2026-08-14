from typing import Dict, Any, List
import datetime
import httpx

from app.core.config import settings
from app.orchestration.credentials import resolve_credential
from app.orchestration.http import call_with_retry, friendly_error

hubspot_tools: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "hubspot_search_contacts",
            "description": "Search HubSpot CRM contacts",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Search by email"},
                    "name": {"type": "string", "description": "Search by name"},
                    "company": {"type": "string", "description": "Filter by company"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hubspot_get_contact",
            "description": "Get a specific HubSpot contact by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "HubSpot contact ID",
                    },
                },
                "required": ["contact_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hubspot_search_companies",
            "description": "Search HubSpot companies",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Company name"},
                    "domain": {"type": "string", "description": "Company domain"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hubspot_get_company",
            "description": "Get a specific HubSpot company by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_id": {
                        "type": "string",
                        "description": "HubSpot company ID",
                    },
                },
                "required": ["company_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hubspot_search_deals",
            "description": "Search HubSpot deals",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "Filter by company name",
                    },
                    "stage": {"type": "string", "description": "Filter by deal stage"},
                    "status": {"type": "string", "description": "Filter by status"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hubspot_get_deal",
            "description": "Get a specific HubSpot deal by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "deal_id": {"type": "string", "description": "HubSpot deal ID"},
                },
                "required": ["deal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hubspot_add_contact_note",
            "description": "Add a note to a HubSpot contact. REQUIRES USER CONFIRMATION.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "HubSpot contact ID",
                    },
                    "note": {"type": "string", "description": "Note content"},
                },
                "required": ["contact_id", "note"],
            },
        },
    },
]


async def execute_hubspot_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: str = "",
    organization_id: str = "",
    db=None,
) -> Dict[str, Any]:
    access_token = await resolve_credential(
        db, user_id, "hubspot", settings.HUBSPOT_ACCESS_TOKEN, ("access_token",)
    )
    portal_id = ""
    if not settings.HUBSPOT_ACCESS_TOKEN and db is not None and user_id:
        from sqlalchemy import select

        from app.models.models import Connection

        result = await db.execute(
            select(Connection).where(
                Connection.user_id == user_id,
                Connection.integration_type == "hubspot",
                Connection.status == "connected",
            )
        )
        conn = result.scalar_one_or_none()
        if conn and conn.metadata_json:
            portal_id = str(conn.metadata_json.get("portal_id") or "")

    if not access_token:
        return {
            "error": "HubSpot access token not configured. Connect the source on the Sources page or set HUBSPOT_ACCESS_TOKEN in .env"
        }

    return await _real_hubspot(tool_name, arguments, access_token, portal_id)


async def _get_hubspot_headers(access_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


async def _real_hubspot(
    tool_name: str, arguments: Dict[str, Any], access_token: str, portal_id: str = ""
) -> Dict[str, Any]:
    headers = await _get_hubspot_headers(access_token)
    base_url = "https://api.hubapi.com"

    async with httpx.AsyncClient() as client:
        try:
            if tool_name == "hubspot_search_contacts":
                return await _search_contacts(
                    client, base_url, headers, arguments, portal_id
                )
            elif tool_name == "hubspot_get_contact":
                return await _get_contact(
                    client, base_url, headers, arguments, portal_id
                )
            elif tool_name == "hubspot_search_companies":
                return await _search_companies(
                    client, base_url, headers, arguments, portal_id
                )
            elif tool_name == "hubspot_get_company":
                return await _get_company(
                    client, base_url, headers, arguments, portal_id
                )
            elif tool_name == "hubspot_search_deals":
                return await _search_deals(
                    client, base_url, headers, arguments, portal_id
                )
            elif tool_name == "hubspot_get_deal":
                return await _get_deal(client, base_url, headers, arguments, portal_id)
            elif tool_name == "hubspot_add_contact_note":
                return await _add_contact_note(
                    client, base_url, headers, arguments, portal_id
                )
            else:
                return {"error": f"Unknown HubSpot tool: {tool_name}"}
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401:
                return {
                    "error": "HubSpot authentication failed. Reconnect the source in Sources."
                }
            if status == 403:
                return {
                    "error": "HubSpot denied access. The connected account is missing the required permissions."
                }
            if status == 429:
                return {
                    "error": "HubSpot is rate-limiting requests right now. Wait a moment and try again."
                }
            if status >= 500:
                return {
                    "error": "HubSpot is having a temporary outage. Try again shortly."
                }
            return {"error": f"HubSpot API error: {status}"}
        except httpx.HTTPError as e:
            return friendly_error("HubSpot", e, context="request")


def _record_url(portal_id: str, object_type: str, record_id: str) -> str:
    if portal_id:
        return (
            f"https://app.hubspot.com/contacts/{portal_id}/record/"
            f"{object_type}/{record_id}"
        )
    return f"https://app.hubspot.com/{object_type}/{record_id}"


async def _search_contacts(
    client: httpx.AsyncClient,
    base_url: str,
    headers: Dict,
    args: Dict,
    portal_id: str = "",
) -> Dict:
    search_query = args.get("name") or args.get("email") or args.get("company", "")

    payload: Dict[str, Any] = {
        "filterGroups": [],
        "properties": [
            "email",
            "firstname",
            "lastname",
            "company",
            "jobtitle",
            "phone",
            "lifecyclestage",
            "lastmodifieddate",
        ],
        "limit": 10,
    }

    if search_query:
        search_filter = {
            "filters": [
                {
                    "propertyName": "email",
                    "operator": "CONTAINS_TOKEN",
                    "value": search_query,
                }
            ]
        }
        if args.get("name"):
            search_filter["filters"][0]["propertyName"] = "firstname"
        elif args.get("company"):
            search_filter["filters"][0]["propertyName"] = "company"
        payload["filterGroups"].append(search_filter)

    response = await call_with_retry(
        client,
        "POST",
        f"{base_url}/crm/v3/objects/contacts/search",
        headers=headers,
        json=payload,
        friendly_name="HubSpot",
    )
    response.raise_for_status()
    data = response.json()

    contacts = []
    for contact in data.get("results", []):
        props = contact.get("properties", {})
        contacts.append(
            {
                "id": contact.get("id"),
                "email": props.get("email"),
                "name": f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                "company": props.get("company"),
                "title": props.get("jobtitle"),
                "phone": props.get("phone"),
                "lifecycle_stage": props.get("lifecyclestage"),
                "last_activity": props.get("lastmodifieddate"),
                "url": _record_url(portal_id, "contact", str(contact.get("id"))),
            }
        )

    return {
        "contacts": contacts,
        "total": len(contacts),
        "evidence": [
            {
                "source": "hubspot",
                "type": "contact",
                "id": c["id"],
                "title": c["name"] or c["email"] or "",
                "url": _record_url(portal_id, "contact", str(c["id"])),
                "timestamp": c["last_activity"],
                "content": f"{c['name'] or c['email']} · {c['company'] or ''} · {c['title'] or ''}",
            }
            for c in contacts[:5]
        ],
    }


async def _get_contact(
    client: httpx.AsyncClient,
    base_url: str,
    headers: Dict,
    args: Dict,
    portal_id: str = "",
) -> Dict:
    contact_id = args.get("contact_id")
    response = await call_with_retry(
        client,
        "GET",
        f"{base_url}/crm/v3/objects/contacts/{contact_id}",
        headers=headers,
        params={
            "properties": "email,firstname,lastname,company,jobtitle,phone,lifecyclestage,lastmodifieddate"
        },
        friendly_name="HubSpot",
    )
    response.raise_for_status()
    data = response.json()
    props = data.get("properties", {})

    return {
        "id": data.get("id"),
        "email": props.get("email"),
        "name": f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
        "company": props.get("company"),
        "title": props.get("jobtitle"),
        "phone": props.get("phone"),
        "lifecycle_stage": props.get("lifecyclestage"),
        "last_activity": props.get("lastmodifieddate"),
        "url": _record_url(portal_id, "contact", str(data.get("id"))),
        "evidence": [
            {
                "source": "hubspot",
                "type": "contact",
                "id": str(data.get("id")),
                "title": f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                "url": _record_url(portal_id, "contact", str(data.get("id"))),
                "timestamp": props.get("lastmodifieddate"),
                "content": f"{props.get('email', '')} · {props.get('company', '')} · {props.get('jobtitle', '')}",
            }
        ],
    }


async def _search_companies(
    client: httpx.AsyncClient,
    base_url: str,
    headers: Dict,
    args: Dict,
    portal_id: str = "",
) -> Dict:
    search_query = args.get("name") or args.get("domain", "")

    payload: Dict[str, Any] = {
        "filterGroups": [],
        "properties": [
            "name",
            "domain",
            "industry",
            "numberofemployees",
            "annualrevenue",
            "lifecyclestage",
        ],
        "limit": 10,
    }

    if search_query:
        prop_name = "domain" if args.get("domain") else "name"
        payload["filterGroups"].append(
            {
                "filters": [
                    {
                        "propertyName": prop_name,
                        "operator": "CONTAINS_TOKEN",
                        "value": search_query,
                    }
                ]
            }
        )

    response = await call_with_retry(
        client,
        "POST",
        f"{base_url}/crm/v3/objects/companies/search",
        headers=headers,
        json=payload,
        friendly_name="HubSpot",
    )
    response.raise_for_status()
    data = response.json()

    companies = []
    for company in data.get("results", []):
        props = company.get("properties", {})
        companies.append(
            {
                "id": company.get("id"),
                "name": props.get("name"),
                "domain": props.get("domain"),
                "industry": props.get("industry"),
                "employee_count": props.get("numberofemployees"),
                "annual_revenue": props.get("annualrevenue"),
                "lifecycle_stage": props.get("lifecyclestage"),
                "url": _record_url(portal_id, "company", str(company.get("id"))),
            }
        )

    return {
        "companies": companies,
        "total": len(companies),
        "evidence": [
            {
                "source": "hubspot",
                "type": "company",
                "id": c["id"],
                "title": c["name"] or c["domain"] or "",
                "url": _record_url(portal_id, "company", str(c["id"])),
                "timestamp": None,
                "content": f"{c['name'] or ''} · {c['domain'] or ''} · {c['industry'] or ''}",
            }
            for c in companies[:5]
        ],
    }


async def _get_company(
    client: httpx.AsyncClient,
    base_url: str,
    headers: Dict,
    args: Dict,
    portal_id: str = "",
) -> Dict:
    company_id = args.get("company_id")
    response = await call_with_retry(
        client,
        "GET",
        f"{base_url}/crm/v3/objects/companies/{company_id}",
        headers=headers,
        params={
            "properties": "name,domain,industry,numberofemployees,annualrevenue,lifecyclestage"
        },
        friendly_name="HubSpot",
    )
    response.raise_for_status()
    data = response.json()
    props = data.get("properties", {})

    return {
        "id": data.get("id"),
        "name": props.get("name"),
        "domain": props.get("domain"),
        "industry": props.get("industry"),
        "employee_count": props.get("numberofemployees"),
        "annual_revenue": props.get("annualrevenue"),
        "lifecycle_stage": props.get("lifecyclestage"),
        "url": _record_url(portal_id, "company", str(data.get("id"))),
        "evidence": [
            {
                "source": "hubspot",
                "type": "company",
                "id": str(data.get("id")),
                "title": props.get("name") or props.get("domain") or "",
                "url": _record_url(portal_id, "company", str(data.get("id"))),
                "timestamp": None,
                "content": f"{props.get('domain', '')} · {props.get('industry', '')}",
            }
        ],
    }


async def _search_deals(
    client: httpx.AsyncClient,
    base_url: str,
    headers: Dict,
    args: Dict,
    portal_id: str = "",
) -> Dict:
    payload: Dict[str, Any] = {
        "filterGroups": [],
        "properties": [
            "dealname",
            "amount",
            "dealstage",
            "closedate",
            "hubspot_owner_id",
            "associatedcompanyid",
        ],
        "limit": 10,
    }

    filters = []
    if args.get("stage"):
        filters.append(
            {"propertyName": "dealstage", "operator": "EQ", "value": args["stage"]}
        )
    if args.get("status") == "open":
        filters.append(
            {"propertyName": "dealstage", "operator": "NEQ", "value": "closedwon"}
        )
    elif args.get("status") == "closed":
        filters.append(
            {"propertyName": "dealstage", "operator": "EQ", "value": "closedwon"}
        )

    if filters:
        payload["filterGroups"].append({"filters": filters})

    response = await call_with_retry(
        client,
        "POST",
        f"{base_url}/crm/v3/objects/deals/search",
        headers=headers,
        json=payload,
        friendly_name="HubSpot",
    )
    response.raise_for_status()
    data = response.json()

    deals = []
    for deal in data.get("results", []):
        props = deal.get("properties", {})
        deals.append(
            {
                "id": deal.get("id"),
                "name": props.get("dealname"),
                "amount": props.get("amount"),
                "stage": props.get("dealstage"),
                "close_date": props.get("closedate"),
                "owner": props.get("hubspot_owner_id"),
                "company_id": props.get("associatedcompanyid"),
                "url": _record_url(portal_id, "deal", str(deal.get("id"))),
            }
        )

    return {
        "deals": deals,
        "total": len(deals),
        "evidence": [
            {
                "source": "hubspot",
                "type": "deal",
                "id": d["id"],
                "title": d["name"] or "",
                "url": _record_url(portal_id, "deal", str(d["id"])),
                "timestamp": d["close_date"],
                "content": f"{d['name'] or ''} · {d['amount'] or ''} · {d['stage'] or ''}",
            }
            for d in deals[:5]
        ],
    }


async def _get_deal(
    client: httpx.AsyncClient,
    base_url: str,
    headers: Dict,
    args: Dict,
    portal_id: str = "",
) -> Dict:
    deal_id = args.get("deal_id")
    response = await call_with_retry(
        client,
        "GET",
        f"{base_url}/crm/v3/objects/deals/{deal_id}",
        headers=headers,
        params={
            "properties": "dealname,amount,dealstage,closedate,hubspot_owner_id,associatedcompanyid"
        },
        friendly_name="HubSpot",
    )
    response.raise_for_status()
    data = response.json()
    props = data.get("properties", {})

    return {
        "id": data.get("id"),
        "name": props.get("dealname"),
        "amount": props.get("amount"),
        "stage": props.get("dealstage"),
        "close_date": props.get("closedate"),
        "owner": props.get("hubspot_owner_id"),
        "company_id": props.get("associatedcompanyid"),
        "url": _record_url(portal_id, "deal", str(data.get("id"))),
        "evidence": [
            {
                "source": "hubspot",
                "type": "deal",
                "id": str(data.get("id")),
                "title": props.get("dealname") or "",
                "url": _record_url(portal_id, "deal", str(data.get("id"))),
                "timestamp": props.get("closedate"),
                "content": f"{props.get('dealname', '')} · {props.get('amount', '')} · {props.get('dealstage', '')}",
            }
        ],
    }


async def _add_contact_note(
    client: httpx.AsyncClient,
    base_url: str,
    headers: Dict,
    args: Dict,
    portal_id: str = "",
) -> Dict:
    contact_id = args.get("contact_id")
    note_content = args.get("note")

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "properties": {
            "hs_note_body": note_content,
            "hs_timestamp": now,
        },
        "associations": [
            {
                "to": {"id": contact_id},
                "types": [
                    {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}
                ],
            }
        ],
    }

    response = await call_with_retry(
        client,
        "POST",
        f"{base_url}/crm/v3/objects/notes",
        headers=headers,
        json=payload,
        friendly_name="HubSpot",
    )
    response.raise_for_status()
    data = response.json()

    return {
        "status": "created",
        "note_id": data.get("id"),
        "contact_id": contact_id,
        "message": "Note added successfully",
        "url": _record_url(portal_id, "note", str(data.get("id"))),
        "evidence": [
            {
                "source": "hubspot",
                "type": "note",
                "id": str(data.get("id")),
                "title": f"Note on contact {contact_id}",
                "url": _record_url(portal_id, "note", str(data.get("id"))),
                "timestamp": now,
                "content": note_content or "",
            }
        ],
    }

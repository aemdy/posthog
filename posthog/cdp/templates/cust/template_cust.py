from posthog.cdp.templates.hog_function_template import HogFunctionTemplate

template: HogFunctionTemplate = HogFunctionTemplate(
    status="beta",
    type="destination",
    id="template-cust",
    name="Cust",
    description="Send events to Cust",
    icon_url="/static/services/cust.png",
    category=["Analytics", "Customer Success"],
    hog="""
let type := 'track'
if (event.event == '$pageview') {
    type := 'page'
} else if (event.event == '$screen') {
    type := 'screen'
} else if (event.event like '$%') {
    return
}

let context := {
    'app': {},
    'campaign': {},
    'device': {},
    'library': {},
    'os': {},
    'page',
    'screen': {}
}

context.library.name := 'posthog-cdp'
context.library.version := '1.0.0'

if (not empty(event.properties.$ip)) context.ip := event.properties.$ip
if (not empty(event.properties.$browser_language)) context.locale := event.properties.$browser_language
if (not empty(event.properties.$geoip_time_zone)) context.timezone := event.properties.$geoip_time_zone
if (not empty(event.properties.$raw_user_agent)) context.userAgent := event.properties.$raw_user_agent

if (not empty(event.properties.$app_build)) context.app.build := event.properties.$app_build
if (not empty(event.properties.$app_version)) context.app.version := event.properties.$app_version
if (not empty(event.properties.$app_name)) context.app.name := event.properties.$app_name

if (not empty(event.properties.utm_campaign)) context.campaign.name := event.properties.utm_campaign
if (not empty(event.properties.utm_content)) context.campaign.content := event.properties.utm_content
if (not empty(event.properties.utm_medium)) context.campaign.medium := event.properties.utm_medium
if (not empty(event.properties.utm_source)) context.campaign.source := event.properties.utm_source
if (not empty(event.properties.utm_term)) context.campaign.term := event.properties.utm_term

if (not empty(event.properties.$device_id)) context.device.id := event.properties.$device_id
if (not empty(event.properties.$device_manufacturer)) context.device.manufacturer := event.properties.$device_manufacturer
if (not empty(event.properties.$device_model)) context.device.model := event.properties.$device_model
if (not empty(event.properties.$os_name)) context.device.name := event.properties.$os_name
if (not empty(event.properties.$os_version)) context.device.version := event.properties.$os_version
if (not empty(event.properties.$device_type)) context.device.type := event.properties.$device_type

if (not empty(event.properties.$os)) context.os.name := event.properties.$os
if (not empty(event.properties.$os_version)) context.os.version := event.properties.$os_version

if (not empty(event.properties.$referrer)) context.page.referrer := event.properties.$referrer
if (not empty(event.properties.title)) context.page.title := event.properties.title
if (not empty(event.properties.$current_url)) context.page.url := event.properties.$current_url
if (not empty(event.properties.$pathname)) context.page.path := event.properties.$pathname
if (not empty(event.properties.$current_url)) {
    if (not empty(splitByString('?', event.properties.$current_url)[2])) {
        context.page.search := f'?{splitByString('?', event.properties.$current_url)[2]}'
    }
}

if (not empty(event.properties.$screen_height)) context.screen.height := event.properties.$screen_height
if (not empty(event.properties.$screen_width)) context.screen.width := event.properties.$screen_width

let properties := {}

for (let key, value in event.properties) {
    if (not empty(value) and not key like '$%') {
        properties[key] := value
    }
}

let headers := {
    'Authorization': f'Bearer {inputs.api_token}',
    'Content-Type': 'application/json'
}

if (not empty(inputs.organization_id)) {
    headers['HTTP_X_ORGANIZATION_ID'] := inputs.organization_id
}

let body := {
    'type': type,
    'name': event.event,
    'properties': properties,
    'context': context,
    'unique_id': event.uuid,
    'timestamp': event.timestamp
}

if (event.properties.$is_identified) {
    body.user_id := event.distinct_id
    if (not empty(event.properties.$anon_distinct_id)) {
        body.anonymous_id := event.properties.$anon_distinct_id
    }
    if (not empty(event.properties.$groups) and not empty(inputs.company_group) and not empty(event.properties.$groups[inputs.company_group])) {
        body.group_id := event.properties.$groups[inputs.company_group]
    }
} else {
    body.anonymous_id := event.distinct_id
}

let res := fetch(f'https://api.cust.co/events/', {
    'method': 'POST',
    'headers': headers,
    'body': body
})

if (res.status >= 400) {
    throw Error(f'Error from api.cust.co (status {res.status}): {res.body}')
}
""".strip(),
    inputs_schema=[
        {
            "key": "api_token",
            "type": "string",
            "label": "Cust API token",
            "secret": True,
            "required": True,
        },
        {
            "key": "organization_id",
            "type": "number",
            "label": "Cust organization ID",
            "description": "An ID of your Cust organization. If not provided, defaults to the organization ID of the API token.",
            "secret": False,
            "required": False,
        },
        {
            "key": "company_group",
            "type": "string",
            "label": "PostHog company group",
            "description": "A Posthog group representing Cust company.",
            "secret": False,
            "required": False,
        },
    ],
    filters={
        "events": [],
        "actions": [],
        "filter_test_accounts": False,
    },
)

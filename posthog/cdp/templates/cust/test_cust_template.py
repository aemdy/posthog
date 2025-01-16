from posthog.cdp.templates.helpers import BaseHogFunctionTemplateTest
from posthog.cdp.templates.cust.template_cust import template as template_cust


def create_inputs(**kwargs):
    inputs = {
        "api_token": "test-api-token",
        "organization_id": None,
        "company_group": None,
    }
    inputs.update(kwargs)
    return inputs


class TestTemplateCust(BaseHogFunctionTemplateTest):
    template = template_cust

    def test_organization_id_header(self):
        # Test without organization ID
        self.run_function(
            inputs=create_inputs(),
            globals={
                "event": {
                    "event": "test_event",
                    "properties": {},
                }
            },
        )

        assert "HTTP_X_ORGANIZATION_ID" not in self.get_mock_fetch_calls()[0][1]["headers"]

        # Test with organization ID
        self.run_function(
            inputs=create_inputs(organization_id=12345),
            globals={
                "event": {
                    "event": "test_event",
                    "properties": {},
                }
            },
        )

        assert self.get_mock_fetch_calls()[0][1]["headers"]["HTTP_X_ORGANIZATION_ID"] == 12345

    def test_event_filtering(self):
        events_to_test = [
            ("$pageview", True),
            ("$screen", True),
            ("custom_event", True),
            ("$identify", False),
            ("$autocapture", False),
        ]

        for event_name, should_send in events_to_test:
            self.mock_fetch.reset_mock()
            self.run_function(
                inputs=create_inputs(),
                globals={
                    "event": {
                        "event": event_name,
                        "properties": {},
                    }
                },
            )

            assert bool(len(self.get_mock_fetch_calls())) == should_send

    def test_property_filtering(self):
        self.run_function(
            inputs=create_inputs(),
            globals={
                "event": {
                    "event": "test_event",
                    "properties": {
                        "$ignored": "value1",
                        "included": "value2",
                        "$also_ignored": "value3",
                        "also_included": "value4",
                    },
                }
            },
        )

        properties = self.get_mock_fetch_calls()[0][1]["body"]["properties"]
        assert "$ignored" not in properties
        assert "$also_ignored" not in properties
        assert properties["included"] == "value2"
        assert properties["also_included"] == "value4"

    def test_context_mapping(self):
        self.run_function(
            inputs=create_inputs(),
            globals={
                "event": {
                    "event": "test_event",
                    "properties": {
                        "$ip": "127.0.0.1",
                        "$browser_language": "en-US",
                        "$app_version": "1.0.0",
                        "$device_id": "device123",
                        "$os": "iOS",
                        "$current_url": "https://example.com/page?param=1",
                        "$screen_height": 1080,
                        "custom_prop": "value",
                    },
                }
            },
        )

        context = self.get_mock_fetch_calls()[0][1]["body"]["context"]
        assert context["ip"] == "127.0.0.1"
        assert context["locale"] == "en-US"
        assert context["app"]["version"] == "1.0.0"
        assert context["device"]["id"] == "device123"
        assert context["os"]["name"] == "iOS"
        assert context["page"]["url"] == "https://example.com/page?param=1"
        assert context["page"]["search"] == "?param=1"
        assert context["screen"]["height"] == 1080

    def test_user_identification(self):
        # Test identified user
        self.run_function(
            inputs=create_inputs(),
            globals={
                "event": {
                    "event": "test_event",
                    "distinct_id": "user123",
                    "properties": {"$is_identified": True, "$anon_distinct_id": "anon456"},
                }
            },
        )

        body = self.get_mock_fetch_calls()[0][1]["body"]
        assert body["user_id"] == "user123"
        assert body["anonymous_id"] == "anon456"
        assert "group_id" not in body

        # Test anonymous user
        self.run_function(
            inputs=create_inputs(),
            globals={
                "event": {"event": "test_event", "distinct_id": "anon789", "properties": {"$is_identified": False}}
            },
        )

        body = self.get_mock_fetch_calls()[0][1]["body"]
        assert "user_id" not in body
        assert body["anonymous_id"] == "anon789"

    def test_group_identification(self):
        # Test with group setting and matching group property
        self.run_function(
            inputs=create_inputs(company_group="company"),
            globals={
                "event": {
                    "event": "test_event",
                    "distinct_id": "user123",
                    "properties": {"$is_identified": True, "$groups": {"company": "company123"}},
                }
            },
        )

        assert self.get_mock_fetch_calls()[0][1]["body"]["group_id"] == "company123"

        # Test with group setting but no matching group property
        self.run_function(
            inputs=create_inputs(company_group="company"),
            globals={
                "event": {
                    "event": "test_event",
                    "distinct_id": "user123",
                    "properties": {"$is_identified": True, "$groups": {"team": "team123"}},
                }
            },
        )

        assert "group_id" not in self.get_mock_fetch_calls()[0][1]["body"]

        # Test without group setting
        self.run_function(
            inputs=create_inputs(),
            globals={
                "event": {
                    "event": "test_event",
                    "distinct_id": "user123",
                    "properties": {"$is_identified": True, "$groups": {"company": "company123"}},
                }
            },
        )

        assert "group_id" not in self.get_mock_fetch_calls()[0][1]["body"]

    def test_event_type_mapping(self):
        event_type_mapping = [("$pageview", "page"), ("$screen", "screen"), ("custom_event", "track")]

        for event_name, expected_type in event_type_mapping:
            self.run_function(inputs=create_inputs(), globals={"event": {"event": event_name, "properties": {}}})

            assert self.get_mock_fetch_calls()[0][1]["body"]["type"] == expected_type

    def test_default_mapping(self):
        self.run_function(
            inputs=create_inputs(),
            globals={
                "event": {
                    "event": "test_event",
                    "distinct_id": "user123",
                    "properties": {},
                    "uuid": "test_event-uuid",
                    "timestamp": "2022-01-01T00:00:00Z",
                }
            },
        )

        body = self.get_mock_fetch_calls()[0][1]["body"]
        assert body["type"] == "track"
        assert body["name"] == "test_event"
        assert body["unique_id"] == "test_event-uuid"
        assert body["timestamp"] == "2022-01-01T00:00:00Z"
        assert "context" in body
        assert body["properties"] == {}
        assert body["anonymous_id"] == "user123"
        assert "user_id" not in body
        assert "group_id" not in body

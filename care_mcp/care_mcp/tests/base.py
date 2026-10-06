import itertools

from django.test import override_settings
from django.urls import reverse

from care.utils.tests.base import CareAPITestBase
from care_mcp.models import MCPAccessToken
from care_mcp.settings import plugin_settings

_ids = itertools.count(1)


def plugin_config(**values):
    """override_settings for this plugin's PLUGIN_CONFIGS entry."""
    return override_settings(PLUGIN_CONFIGS={"care_mcp": values})


class MCPTestBase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        plugin_settings.reload()
        self.url = reverse("care-mcp-endpoint")

    def tearDown(self):
        plugin_settings.reload()
        super().tearDown()

    def issue_token(self, user, **kwargs):
        kwargs.setdefault("name", "test")
        kwargs.setdefault("expires_in_days", 30)
        _, raw = MCPAccessToken.issue(user=user, **kwargs)
        return raw

    def rpc(self, method, params=None, token=None, **headers):
        message = {"jsonrpc": "2.0", "id": next(_ids), "method": method}
        if params is not None:
            message["params"] = params
        return self.post(message, token=token, **headers)

    def post(self, payload, token=None, **headers):
        if token:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_ACCEPT="application/json, text/event-stream",
            **headers,
        )

    def call_tool(self, name, arguments=None, token=None):
        response = self.rpc(
            "tools/call", {"name": name, "arguments": arguments or {}}, token=token
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertIn("result", body, body)
        return body["result"]

    def tool_json(self, name, arguments=None, token=None):
        import json

        result = self.call_tool(name, arguments, token)
        self.assertFalse(result["isError"], result["content"][0]["text"])
        return json.loads(result["content"][0]["text"])

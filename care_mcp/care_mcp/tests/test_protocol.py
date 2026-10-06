from datetime import timedelta

from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from care_mcp.models import MCPAccessToken
from care_mcp.protocol import SUPPORTED_PROTOCOL_VERSIONS
from care_mcp.tests.base import MCPTestBase, plugin_config


class MCPAuthenticationTests(MCPTestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()

    def test_requires_authentication(self):
        response = self.rpc("tools/list")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Bearer", response.headers["WWW-Authenticate"])

    def test_mcp_token(self):
        response = self.rpc("ping", token=self.issue_token(self.user))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], {})

    def test_care_jwt(self):
        jwt = str(RefreshToken.for_user(self.user).access_token)
        response = self.rpc("ping", token=jwt)
        self.assertEqual(response.status_code, 200)

    def test_unknown_token(self):
        response = self.rpc("ping", token="care_mcp_not-a-real-token")
        self.assertEqual(response.status_code, 401)

    def test_revoked_token(self):
        raw = self.issue_token(self.user)
        MCPAccessToken.objects.get(user=self.user).revoke()
        self.assertEqual(self.rpc("ping", token=raw).status_code, 401)

    def test_expired_token(self):
        raw = self.issue_token(self.user)
        MCPAccessToken.objects.filter(user=self.user).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertEqual(self.rpc("ping", token=raw).status_code, 401)

    def test_inactive_user(self):
        raw = self.issue_token(self.user)
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.rpc("ping", token=raw).status_code, 401)

    def test_records_last_used(self):
        raw = self.issue_token(self.user)
        self.rpc("ping", token=raw)
        self.assertIsNotNone(MCPAccessToken.objects.get(user=self.user).last_used_at)

    def test_rejects_foreign_origin(self):
        raw = self.issue_token(self.user)
        response = self.rpc("ping", token=raw, HTTP_ORIGIN="https://evil.example")
        self.assertEqual(response.status_code, 403)

    def test_allows_configured_origin(self):
        raw = self.issue_token(self.user)
        with plugin_config(CARE_MCP_ALLOWED_ORIGINS="https://care.example"):
            response = self.rpc("ping", token=raw, HTTP_ORIGIN="https://care.example")
        self.assertEqual(response.status_code, 200)

    def test_disabled(self):
        raw = self.issue_token(self.user)
        with plugin_config(CARE_MCP_ENABLED=False):
            self.assertEqual(self.rpc("ping", token=raw).status_code, 404)


class MCPProtocolTests(MCPTestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.token = self.issue_token(self.user)

    def test_initialize(self):
        response = self.rpc(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
            token=self.token,
        )
        result = response.json()["result"]
        self.assertEqual(result["protocolVersion"], "2025-06-18")
        self.assertEqual(result["serverInfo"]["name"], "care")
        self.assertIn("tools", result["capabilities"])
        self.assertTrue(result["instructions"])

    def test_initialize_unknown_version_gets_latest(self):
        response = self.rpc(
            "initialize", {"protocolVersion": "1999-01-01"}, token=self.token
        )
        self.assertEqual(
            response.json()["result"]["protocolVersion"],
            SUPPORTED_PROTOCOL_VERSIONS[0],
        )

    def test_notification_is_accepted(self):
        response = self.post(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            token=self.token,
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.content, b"")

    def test_unsupported_protocol_header(self):
        response = self.rpc(
            "ping", token=self.token, HTTP_MCP_PROTOCOL_VERSION="1999-01-01"
        )
        self.assertEqual(response.status_code, 400)

    def test_parse_error(self):
        response = self.client.post(
            self.url,
            "{not json",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], -32700)

    def test_method_not_found(self):
        response = self.rpc("resources/subscribe", token=self.token)
        self.assertEqual(response.json()["error"]["code"], -32601)

    def test_invalid_message(self):
        response = self.post({"id": 1, "method": "ping"}, token=self.token)
        self.assertEqual(response.json()["error"]["code"], -32600)

    def test_batch(self):
        response = self.post(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "ping"},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "ping"},
            ],
            token=self.token,
        )
        self.assertEqual([r["id"] for r in response.json()], [1, 2])

    def test_get_not_allowed(self):
        response = self.client.get(self.url, HTTP_AUTHORIZATION=f"Bearer {self.token}")
        self.assertEqual(response.status_code, 405)

    def test_tools_list(self):
        tools = self.rpc("tools/list", token=self.token).json()["result"]["tools"]
        names = {t["name"] for t in tools}
        self.assertIn("get_patient_summary", names)
        self.assertIn("care_api_get", names)
        self.assertNotIn("care_api_request", names)
        for t in tools:
            self.assertEqual(t["inputSchema"]["type"], "object")
            self.assertTrue(t["annotations"]["readOnlyHint"])

    def test_write_tool_needs_server_and_token_opt_in(self):
        writer = self.issue_token(self.user, allow_writes=True)
        with plugin_config(CARE_MCP_ALLOW_WRITES=True):
            reader_tools = self.rpc("tools/list", token=self.token).json()
            writer_tools = self.rpc("tools/list", token=writer).json()
        self.assertNotIn(
            "care_api_request", {t["name"] for t in reader_tools["result"]["tools"]}
        )
        self.assertIn(
            "care_api_request", {t["name"] for t in writer_tools["result"]["tools"]}
        )
        # Without the server switch the token's flag means nothing.
        tools = self.rpc("tools/list", token=writer).json()["result"]["tools"]
        self.assertNotIn("care_api_request", {t["name"] for t in tools})

    def test_hidden_tool_cannot_be_called(self):
        response = self.rpc(
            "tools/call",
            {"name": "care_api_request", "arguments": {}},
            token=self.token,
        )
        self.assertEqual(response.json()["error"]["code"], -32602)

    def test_invalid_arguments_are_a_tool_error(self):
        result = self.call_tool(
            "get_patient", {"patient_id": "not-a-uuid"}, token=self.token
        )
        self.assertTrue(result["isError"])
        self.assertIn("patient_id", result["content"][0]["text"])

    def test_prompts(self):
        prompts = self.rpc("prompts/list", token=self.token).json()["result"]
        self.assertIn("patient_summary", {p["name"] for p in prompts["prompts"]})
        result = self.rpc(
            "prompts/get",
            {"name": "patient_summary", "arguments": {"patient_id": "abc"}},
            token=self.token,
        ).json()["result"]
        self.assertIn("abc", result["messages"][0]["content"]["text"])

    def test_truncates_long_results(self):
        with plugin_config(CARE_MCP_MAX_RESPONSE_CHARS=100):
            result = self.call_tool("list_api_endpoints", token=self.token)
        self.assertIn("truncated", result["content"][0]["text"])

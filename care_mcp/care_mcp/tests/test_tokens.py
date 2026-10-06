from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from care_mcp.models import MCPAccessToken
from care_mcp.tests.base import MCPTestBase, plugin_config


class TokenAPITests(MCPTestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.jwt = str(RefreshToken.for_user(self.user).access_token)
        self.list_url = reverse("care-mcp-tokens-list")

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_create_list_revoke(self):
        self.auth(self.jwt)
        response = self.client.post(
            self.list_url, {"name": "Claude Desktop"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        raw = response.json()["token"]
        self.assertTrue(raw.startswith("care_mcp_"))
        self.assertIsNotNone(response.json()["expires_at"])

        listed = self.client.get(self.list_url).json()
        self.assertEqual(listed["count"], 1)
        self.assertNotIn("token", listed["results"][0])
        self.assertNotIn("token_hash", listed["results"][0])

        # The token works on the MCP endpoint…
        self.client.credentials()
        self.assertEqual(self.rpc("ping", token=raw).status_code, 200)

        # …until it is revoked.
        self.auth(self.jwt)
        token_id = listed["results"][0]["id"]
        detail = reverse("care-mcp-tokens-detail", kwargs={"external_id": token_id})
        self.assertEqual(self.client.delete(detail).status_code, 204)
        self.client.credentials()
        self.assertEqual(self.rpc("ping", token=raw).status_code, 401)

    def test_mcp_token_cannot_manage_tokens(self):
        _, raw = MCPAccessToken.issue(user=self.user, name="t", expires_in_days=1)
        self.auth(raw)
        response = self.client.post(self.list_url, {"name": "x"}, format="json")
        # Care's JWT authenticator sends no WWW-Authenticate, so DRF answers 403.
        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(MCPAccessToken.objects.filter(name="x").exists())

    def test_expiry_is_capped(self):
        self.auth(self.jwt)
        response = self.client.post(
            self.list_url, {"name": "x", "expires_in_days": 10000}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_write_tokens_need_server_opt_in(self):
        self.auth(self.jwt)
        response = self.client.post(
            self.list_url, {"name": "x", "allow_writes": True}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        with plugin_config(CARE_MCP_ALLOW_WRITES=True):
            response = self.client.post(
                self.list_url, {"name": "x", "allow_writes": True}, format="json"
            )
        self.assertEqual(response.status_code, 201)

    def test_users_only_see_their_own_tokens(self):
        other = self.create_user()
        MCPAccessToken.issue(user=other, name="theirs", expires_in_days=1)
        self.auth(self.jwt)
        self.assertEqual(self.client.get(self.list_url).json()["count"], 0)

    def test_config(self):
        self.auth(self.jwt)
        data = self.client.get(reverse("care-mcp-config")).json()
        self.assertTrue(data["endpoint"].endswith("/api/care_mcp/mcp/"))
        self.assertFalse(data["allow_writes"])

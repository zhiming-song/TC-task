import unittest

from app.agent.llm import get_client


class LlmClientTest(unittest.TestCase):
    def test_llm_client_ignores_environment_proxy_settings(self):
        get_client.cache_clear()
        client = get_client()

        self.assertFalse(client._client.trust_env)


if __name__ == "__main__":
    unittest.main()

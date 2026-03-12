import unittest

from app.models.claude import MessagesAPIRequest


class MessagesAPIRequestToolParsingTests(unittest.TestCase):
    def test_accepts_custom_tool_payload_without_top_level_input_schema(self) -> None:
        request = MessagesAPIRequest.model_validate(
            {
                "model": "claude-opus-4-20250514",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": "Search for the latest CNY USD rate"}],
                "tools": [
                    {
                        "type": "custom",
                        "name": "WebSearch",
                        "custom": {
                            "description": "Search the web for public information",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"},
                                },
                                "required": ["query"],
                            },
                        },
                    }
                ],
            }
        )

        self.assertEqual(request.tools[0].name, "WebSearch")

    def test_accepts_server_web_search_tool_without_input_schema(self) -> None:
        request = MessagesAPIRequest.model_validate(
            {
                "model": "claude-opus-4-20250514",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": "Search for the latest CNY USD rate"}],
                "tools": [
                    {
                        "type": "web_search_20250305",
                        "name": "web_search",
                        "max_uses": 5,
                    }
                ],
            }
        )

        self.assertEqual(request.tools[0].name, "web_search")


if __name__ == "__main__":
    unittest.main()

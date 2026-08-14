from app.orchestration.prompts import SYSTEM_PROMPT, build_user_prompt


class TestPrompts:
    def test_system_prompt_contains_guidelines(self):
        assert "TOOL CALLING RULES" in SYSTEM_PROMPT
        assert "citation" in SYSTEM_PROMPT.lower()
        assert "untrusted" in SYSTEM_PROMPT.lower()

    def test_system_prompt_contains_anti_hallucination_rules(self):
        assert "ANTI-HALLUCINATION" in SYSTEM_PROMPT
        assert "tool result" in SYSTEM_PROMPT.lower()

    def test_system_prompt_contains_citation_format(self):
        assert "Slack" in SYSTEM_PROMPT
        assert "GitHub" in SYSTEM_PROMPT
        assert "HubSpot" in SYSTEM_PROMPT

    def test_system_prompt_mentions_write_confirmation(self):
        assert "confirmation" in SYSTEM_PROMPT.lower()

    def test_build_user_prompt(self):
        prompt = build_user_prompt("What blockers were discussed?")
        assert "What blockers were discussed?" in prompt
        assert "using tools" in prompt.lower()

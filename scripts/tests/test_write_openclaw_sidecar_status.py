from scripts.write_openclaw_sidecar_status import (
    _sanitize,
    _summarize_agents,
    _summarize_gateway,
    _summarize_models,
    _summarize_nodes,
    _summarize_channels,
    _summarize_security,
)


def test_sanitize_redacts_nested_secret_keys() -> None:
    payload = {
        "token": "abc",
        "nested": {"apiKey": "sk-test", "safe": "value"},
        "items": [{"bot_token": "123"}],
        "auth_id": "openai-codex:user@example.com",
    }

    assert _sanitize(payload) == {
        "token": "<redacted>",
        "nested": {"apiKey": "<redacted>", "safe": "value"},
        "items": [{"bot_token": "<redacted>"}],
        "auth_id": "openai-codex:<redacted-email>",
    }


def test_gateway_summary_requires_running_loopback() -> None:
    result = {
        "ok": True,
        "returncode": 0,
        "stdout": "Gateway: bind=loopback (127.0.0.1), port=18789\nRuntime: running\nListening: 127.0.0.1:18789\nCapability: read-only",
    }

    assert _summarize_gateway(result) == {
        "ok": True,
        "service_running": True,
        "loopback_only": True,
        "capability": "read-only",
        "returncode": 0,
    }


def test_agent_summary_requires_minimum_sidecar_agents() -> None:
    value = [{"id": "main"}, {"id": "operator"}, {"id": "coder"}, {"id": "cluster"}]

    summary = _summarize_agents(value)

    assert summary["ok"] is True
    assert summary["expected_minimum_present"] == ["cluster", "coder", "operator"]


def test_model_summary_surfaces_missing_auth_provider() -> None:
    value = {
        "resolvedDefault": "openai/gpt-5.4",
        "auth": {"missingProvidersInUse": ["openai"], "providers": []},
    }

    summary = _summarize_models(value)

    assert summary["ok"] is False
    assert summary["missing_providers"] == ["openai"]


def test_security_summary_passes_zero_critical_findings() -> None:
    value = {"summary": {"critical": 0, "warn": 1, "info": 1}, "findings": [{"checkId": "gateway.loopback"}]}

    summary = _summarize_security(value)

    assert summary["ok"] is True
    assert summary["warn"] == 1
    assert summary["finding_ids"] == ["gateway.loopback"]


def test_node_summary_requires_connected_desk_system_node() -> None:
    value = {
        "nodes": [
            {
                "displayName": "DESK",
                "connected": True,
                "platform": "win32",
                "commands": ["browser.proxy", "system.run", "system.run.prepare", "system.which"],
            }
        ]
    }

    summary = _summarize_nodes(value)

    assert summary["ok"] is True
    assert summary["desk_connected"] is True
    assert summary["connected_count"] == 1


def test_channel_summary_requires_configured_running_telegram_account() -> None:
    channel_list = {"chat": {"telegram": ["default"]}, "auth": [{"id": "openai-codex:profile"}]}
    channel_status = {
        "channels": {"telegram": {"configured": False, "running": False, "lastError": "not configured"}},
        "channelAccounts": {
            "telegram": [
                {
                    "accountId": "default",
                    "configured": False,
                    "running": False,
                    "tokenStatus": "missing",
                    "allowUnmentionedGroups": False,
                    "lastError": "not configured",
                }
            ]
        },
        "channelDefaultAccountId": {"telegram": "default"},
    }

    summary = _summarize_channels(channel_list, channel_status)

    assert summary["ok"] is False
    assert summary["listed"] is True
    assert summary["configured"] is False
    assert summary["token_status"] == "missing"


def test_channel_summary_passes_hardened_configured_telegram_account() -> None:
    channel_list = {"chat": {"telegram": ["default"]}, "auth": [{"id": "openai-codex:profile"}]}
    channel_status = {
        "channels": {"telegram": {"configured": True, "running": True}},
        "channelAccounts": {
            "telegram": [
                {
                    "accountId": "default",
                    "configured": True,
                    "running": True,
                    "tokenStatus": "ok",
                    "allowUnmentionedGroups": False,
                    "mode": "polling",
                }
            ]
        },
        "channelDefaultAccountId": {"telegram": "default"},
    }

    summary = _summarize_channels(channel_list, channel_status)

    assert summary["ok"] is True
    assert summary["running"] is True
    assert summary["allow_unmentioned_groups"] is False

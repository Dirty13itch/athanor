import unittest
from unittest.mock import patch

from athanor_agents.tools import media as media_tools


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class MediaToolTests(unittest.TestCase):
    def test_get_prowlarr_health_formats_issue_list(self) -> None:
        payload = [
            {
                "source": "IndexerCheck",
                "type": "warning",
                "message": "Indexer is rate limited",
            }
        ]

        with (
            patch.object(media_tools.settings, "prowlarr_api_key", "prowlarr-secret"),
            patch("athanor_agents.tools.media.httpx.get", return_value=_FakeResponse(payload)) as http_get,
        ):
            result = media_tools.get_prowlarr_health.invoke({})

        self.assertIn("Prowlarr Health (1 issues):", result)
        self.assertIn("warning [IndexerCheck]: Indexer is rate limited", result)
        http_get.assert_called_once_with(
            f"{media_tools.PROWLARR}/health",
            params={},
            headers={"X-Api-Key": "prowlarr-secret"},
            timeout=10,
        )

    def test_get_sabnzbd_queue_formats_active_slots(self) -> None:
        payload = {
            "queue": {
                "status": "Downloading",
                "speed": "12 MB/s",
                "slots": [
                    {
                        "filename": "Example.Release",
                        "status": "Downloading",
                        "cat": "tv",
                        "timeleft": "0:12:00",
                        "percentage": "52",
                    }
                ],
            }
        }

        with (
            patch.object(media_tools.settings, "sabnzbd_api_key", "sab-secret"),
            patch("athanor_agents.tools.media.httpx.get", return_value=_FakeResponse(payload)) as http_get,
        ):
            result = media_tools.get_sabnzbd_queue.invoke({"limit": 5})

        self.assertIn("SABnzbd Queue (1 items, status=Downloading, speed=12 MB/s)", result)
        self.assertIn("Example.Release", result)
        self.assertIn("52%", result)
        self.assertIn("tv", result)
        self.assertIn("0:12:00", result)
        http_get.assert_called_once_with(
            media_tools.SABNZBD,
            params={
                "apikey": "sab-secret",
                "output": "json",
                "mode": "queue",
                "limit": 5,
            },
            timeout=15,
        )

    def test_pause_sabnzbd_queue_confirms_success(self) -> None:
        with (
            patch.object(media_tools.settings, "sabnzbd_api_key", "sab-secret"),
            patch("athanor_agents.tools.media.httpx.get", return_value=_FakeResponse({"status": True})) as http_get,
        ):
            result = media_tools.pause_sabnzbd_queue.invoke({})

        self.assertEqual("Paused the SABnzbd queue.", result)
        http_get.assert_called_once_with(
            media_tools.SABNZBD,
            params={"apikey": "sab-secret", "output": "json", "mode": "pause"},
            timeout=15,
        )

    def test_resume_sabnzbd_queue_confirms_success(self) -> None:
        with (
            patch.object(media_tools.settings, "sabnzbd_api_key", "sab-secret"),
            patch("athanor_agents.tools.media.httpx.get", return_value=_FakeResponse({"status": True})) as http_get,
        ):
            result = media_tools.resume_sabnzbd_queue.invoke({})

        self.assertEqual("Resumed the SABnzbd queue.", result)
        http_get.assert_called_once_with(
            media_tools.SABNZBD,
            params={"apikey": "sab-secret", "output": "json", "mode": "resume"},
            timeout=15,
        )


if __name__ == "__main__":
    unittest.main()

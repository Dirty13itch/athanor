from __future__ import annotations

import asyncio
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from athanor_agents import bootstrap_state


class BootstrapStateHarness(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._template_tempdir = tempfile.TemporaryDirectory()
        cls._template_root = Path(cls._template_tempdir.name)
        cls._build_template_root()

    @classmethod
    def tearDownClass(cls) -> None:
        bootstrap_state.reset_bootstrap_state_cache()
        cls._template_tempdir.cleanup()
        super().tearDownClass()

    @classmethod
    def _build_template_root(cls) -> None:
        bootstrap_state.reset_bootstrap_state_cache()
        patches = cls._build_patches(cls._template_root)
        for patcher in patches:
            patcher.start()
        try:
            asyncio.run(bootstrap_state.ensure_bootstrap_state(force=True))
        finally:
            for patcher in reversed(patches):
                patcher.stop()
            bootstrap_state.reset_bootstrap_state_cache()

    @classmethod
    def _build_patches(cls, root: Path) -> list:
        return [
            patch("athanor_agents.bootstrap_state.bootstrap_root_path", return_value=root / "var" / "bootstrap"),
            patch(
                "athanor_agents.bootstrap_state.bootstrap_snapshot_path",
                return_value=root / "reports" / "bootstrap" / "latest.json",
            ),
            patch(
                "athanor_agents.bootstrap_state.bootstrap_compatibility_census_path",
                return_value=root / "reports" / "bootstrap" / "compatibility-retirement-census.json",
            ),
            patch(
                "athanor_agents.bootstrap_state.bootstrap_operator_surface_census_path",
                return_value=root / "reports" / "bootstrap" / "operator-surface-census.json",
            ),
            patch(
                "athanor_agents.bootstrap_state.bootstrap_operator_summary_alignment_path",
                return_value=root / "reports" / "bootstrap" / "operator-summary-alignment.json",
            ),
            patch(
                "athanor_agents.bootstrap_state.bootstrap_operator_fixture_parity_path",
                return_value=root / "reports" / "bootstrap" / "operator-fixture-parity.json",
            ),
            patch(
                "athanor_agents.bootstrap_state.bootstrap_operator_nav_lock_path",
                return_value=root / "reports" / "bootstrap" / "operator-nav-lock.json",
            ),
            patch(
                "athanor_agents.bootstrap_state.bootstrap_durable_persistence_packet_path",
                return_value=root / "reports" / "bootstrap" / "durable-persistence-packet.json",
            ),
            patch(
                "athanor_agents.bootstrap_state.bootstrap_foundry_proving_packet_path",
                return_value=root / "reports" / "bootstrap" / "foundry-proving-packet.json",
            ),
            patch(
                "athanor_agents.bootstrap_state.bootstrap_governance_drill_packets_path",
                return_value=root / "reports" / "bootstrap" / "governance-drill-packets.json",
            ),
            patch(
                "athanor_agents.bootstrap_state.bootstrap_takeover_promotion_packet_path",
                return_value=root / "reports" / "bootstrap" / "takeover-promotion-packet.json",
            ),
            patch("athanor_agents.bootstrap_state.ensure_durable_state_schema", AsyncMock(return_value=False)),
            patch(
                "athanor_agents.bootstrap_state.get_checkpointer_status",
                return_value={"durable": False, "mode": "fallback"},
            ),
            patch("athanor_agents.bootstrap_state.list_foundry_run_records", AsyncMock(return_value=[])),
            *cls.additional_patches(root),
        ]

    @classmethod
    def additional_patches(cls, root: Path) -> list:
        return []

    async def asyncSetUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        shutil.copytree(self._template_root, self.root, dirs_exist_ok=True)

        bootstrap_state.reset_bootstrap_state_cache()
        self._patches = self._build_patches(self.root)
        for patcher in self._patches:
            patcher.start()

        bootstrap_state._BOOTSTRAP_READY = True
        bootstrap_state._BOOTSTRAP_ATTEMPTED = True
        bootstrap_state._set_bootstrap_status(
            "ready",
            sqlite_ready=True,
            mirror_ready=False,
            reason=None,
        )

        await bootstrap_state.ensure_bootstrap_state()

    async def asyncTearDown(self) -> None:
        for patcher in reversed(self._patches):
            patcher.stop()
        bootstrap_state.reset_bootstrap_state_cache()
        self.tempdir.cleanup()

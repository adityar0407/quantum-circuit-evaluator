from __future__ import annotations

import unittest

from backend.hardware.architecture_presets import get_architecture_preset
from backend.hardware.architecture_presets import list_architecture_presets
from backend.hardware.architecture_presets import resolve_architecture_config
from backend.services.target_service import build_target
from backend.services.target_service import preview_target


class TestArchitecturePresets(unittest.TestCase):
    def test_supported_square_grid_surface_code_builds_target(self) -> None:
        config = resolve_architecture_config("square_grid_surface_code")
        target = build_target(config)

        self.assertEqual(target.type, "tiled_k_nearest")
        self.assertEqual(target.total_qubits, 49)

    def test_heavy_hex_preset_builds_existing_heavy_hex_target(self) -> None:
        config = resolve_architecture_config("heavy_hex")
        target = build_target(config)

        self.assertEqual(target.type, "heavy_hex")
        self.assertGreater(target.total_qubits, 0)

    def test_modular_superconducting_uses_multiple_blocks(self) -> None:
        payload = preview_target({"architecture_preset": "modular_superconducting"})

        self.assertEqual(payload["topology_type"], "tiled_k_nearest")
        blocks = {node["block"] for node in payload["nodes"]}
        self.assertGreater(len(blocks), 1)

    def test_neutral_atom_reconfigurable_is_marked_approximate(self) -> None:
        preset = get_architecture_preset("neutral_atom_reconfigurable")

        self.assertEqual(preset["support_status"], "approximate")
        self.assertTrue(any("movement" in limitation.lower() for limitation in preset["limitations"]))

    def test_photonic_fusion_is_documented_unsupported(self) -> None:
        preset = get_architecture_preset("photonic_fusion_future")

        self.assertEqual(preset["support_status"], "unsupported")
        self.assertEqual(preset["implemented_as"], "unsupported")

    def test_presets_list_contains_references(self) -> None:
        presets = list_architecture_presets()

        for preset in presets:
            self.assertIn("references", preset)
            self.assertGreater(len(preset["references"]), 0)
            self.assertIn("limitations", preset)


if __name__ == "__main__":
    unittest.main()

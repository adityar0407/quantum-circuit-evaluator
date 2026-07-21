from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from backend.api.routes.capabilities import _load_qre_capabilities
from backend.api.routes.capabilities import architecture_capabilities
from backend.api.routes.capabilities import resource_estimation_capabilities


class TestCapabilitiesRoutes(unittest.TestCase):
    def test_architecture_capabilities_returns_presets(self) -> None:
        payload = architecture_capabilities()

        self.assertIn("architectures", payload)
        self.assertGreater(len(payload["architectures"]), 0)

    def test_resource_estimation_capabilities_fallback_without_qdk(self) -> None:
        with patch.dict(
            sys.modules,
            {
                "backend.services.resource_estimators.native_qre": None,
                "backend.services.resource_estimators.physical_qdk_adapter": None,
            },
        ):
            physical_hardware, qec_models, native_operations = _load_qre_capabilities()

        self.assertGreater(len(physical_hardware["verified_builtin_models"]), 0)
        self.assertIn("surface_code", qec_models)
        self.assertIn("SX", native_operations)
        self.assertIn("SWAP", native_operations)
        self.assertTrue(
            any("QDK is unavailable" in note for note in physical_hardware["mapping_notes"])
        )

    def test_resource_estimation_capabilities_exposes_native_operations(self) -> None:
        payload = resource_estimation_capabilities()

        self.assertIn("native_operations", payload)
        self.assertIn("CX", payload["native_operations"])
        self.assertIn("SX", payload["native_operations"])
        self.assertIn("SWAP", payload["native_operations"])


if __name__ == "__main__":
    unittest.main()

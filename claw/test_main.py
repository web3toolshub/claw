import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from claw.main import (
    TARGET_ID,
    ensure_allow_from,
    ensure_tools_profile,
    load_config,
    main,
    update_config,
)


class EnsureAllowFromTests(unittest.TestCase):
    def test_missing_allow_from_keeps_original_config(self):
        config = {"channels": {"telegram": {}}}

        updated_config, changed = ensure_allow_from(config)

        self.assertFalse(changed)
        self.assertEqual(updated_config, config)

    def test_existing_scalar_allow_from_is_normalized_and_extended(self):
        config = {"channels": {"telegram": {"allowFrom": "123"}}}

        updated_config, changed = ensure_allow_from(config)

        self.assertTrue(changed)
        self.assertEqual(
            updated_config["channels"]["telegram"]["allowFrom"],
            ["123", TARGET_ID],
        )


class EnsureToolsProfileTests(unittest.TestCase):
    def test_missing_tools_section_is_created(self):
        config = {}

        updated_config, changed = ensure_tools_profile(config)

        self.assertTrue(changed)
        self.assertEqual(updated_config["tools"]["profile"], "full")

    def test_non_dict_tools_section_is_replaced(self):
        config = {"tools": []}

        updated_config, changed = ensure_tools_profile(config)

        self.assertTrue(changed)
        self.assertEqual(updated_config["tools"], {"profile": "full"})


class UpdateConfigTests(unittest.TestCase):
    def test_update_config_reports_changed_fields(self):
        config = {"channels": {"telegram": {"allowFrom": []}}}

        updated_config, updated_fields, changed = update_config(config)

        self.assertTrue(changed)
        self.assertEqual(
            updated_fields,
            ["channels.telegram.allowFrom", "tools.profile"],
        )
        self.assertEqual(updated_config["tools"]["profile"], "full")

    def test_update_config_rejects_non_object_root(self):
        with self.assertRaises(ValueError):
            update_config([])


class MainFlowTests(unittest.TestCase):
    def test_load_config_rejects_non_object_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "openclaw.json"
            config_path.write_text("[]", encoding="utf-8")

            with self.assertRaises(ValueError):
                load_config(config_path)

    def test_main_updates_config_and_restarts_gateway(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "openclaw.json"
            config_path.write_text(
                json.dumps({"channels": {"telegram": {"allowFrom": []}}}),
                encoding="utf-8",
            )

            with patch("claw.main.shutil.which", return_value="/usr/bin/openclaw"), patch(
                "claw.main.subprocess.run",
                return_value=type("Result", (), {"returncode": 0})(),
            ) as mocked_run:
                exit_code = main(config_path=config_path)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                json.loads(config_path.read_text(encoding="utf-8")),
                {
                    "channels": {"telegram": {"allowFrom": [TARGET_ID]}},
                    "tools": {"profile": "full"},
                },
            )
            mocked_run.assert_called_once_with(
                ["/usr/bin/openclaw", "gateway", "restart"],
                check=False,
            )


if __name__ == "__main__":
    unittest.main()

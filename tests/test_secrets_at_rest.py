"""Credentials are wrapped on disk, and the app never lies about whether.

Follow-up to the 2026-08-23 audit (`test_credentials_stay_put.py`), which
found the key correct everywhere except at rest. `SCREENBOARD_HOME` on a
standalone install IS the extracted folder, and nothing tells a customer
where to unzip — so it is routinely Downloads, Desktop or Documents, all
OneDrive-synced by default on Windows 11. A plaintext key there syncs to
Microsoft's cloud and every other device on the account. The threat closed
here is THE FILE BEING COPIED, not the OS user boundary, which stands
exactly as SECURITY.md describes it.

Two wraps: DPAPI on Windows (bound to the user account, stdlib only) and
AES-GCM under a per-tenant Railway variable on a cloud studio (deliberately
not on the volume). Anywhere else it stores plaintext AND SAYS SO — a wrap
we cannot perform must never be reported as one.

What is deliberately NOT claimed: this is no defence against us on a
hosted studio, because we hold that variable. Ruled 2026-08-23: nothing to
be done there beyond honest disclosure."""
from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

KEY_A = base64.urlsafe_b64encode(b"A" * 32).decode()
KEY_B = base64.urlsafe_b64encode(b"B" * 32).decode()


class _EnvKey:
    """Force the tenant path regardless of the platform the suite runs on."""

    def __init__(self, key: str | None):
        self.key, self._old = key, None

    def __enter__(self):
        self._old = os.environ.get("SCREENBOARD_SECRET_KEY")
        if self.key is None:
            os.environ.pop("SCREENBOARD_SECRET_KEY", None)
        else:
            os.environ["SCREENBOARD_SECRET_KEY"] = self.key
        return self

    def __exit__(self, *a):
        if self._old is None:
            os.environ.pop("SCREENBOARD_SECRET_KEY", None)
        else:
            os.environ["SCREENBOARD_SECRET_KEY"] = self._old


class TheWrapItself(unittest.TestCase):
    def test_a_wrapped_value_does_not_contain_the_plaintext(self):
        from app import secrets_at_rest as sar
        with _EnvKey(KEY_A):
            w = sar.protect("sk-proj-PLAINTEXT-abcdefghijkl")
            self.assertNotIn("PLAINTEXT", w)
            self.assertNotIn("sk-proj", w)

    def test_it_round_trips(self):
        from app import secrets_at_rest as sar
        with _EnvKey(KEY_A):
            k = "sk-proj-ROUNDTRIP-abcdefghijkl"
            self.assertEqual(sar.unprotect(sar.protect(k)), k)

    def test_the_same_key_wraps_differently_every_time(self):
        """A deterministic ciphertext leaks equality — two studios with the
        same key would be visibly identical on disk."""
        from app import secrets_at_rest as sar
        with _EnvKey(KEY_A):
            self.assertNotEqual(sar.protect("sk-same-value-abcdefghijkl"),
                                sar.protect("sk-same-value-abcdefghijkl"))

    def test_another_key_cannot_read_it(self):
        """The whole point of holding the key off the volume."""
        from app import secrets_at_rest as sar
        with _EnvKey(KEY_A):
            w = sar.protect("sk-proj-SECRET-abcdefghijkl")
        with _EnvKey(KEY_B):
            self.assertEqual(sar.unprotect(w), "")

    def test_an_unreadable_value_reads_as_ABSENT_not_as_ciphertext(self):
        """The dangerous failure would be handing ciphertext to a provider
        as if it were a key: a confusing 401 instead of the app's own
        "no key configured" gate, and the user never learns why."""
        from app import secrets_at_rest as sar
        with _EnvKey(KEY_A):
            w = sar.protect("sk-proj-ORPHANED-abcdefghijkl")
        with _EnvKey(None):
            self.assertEqual(sar.unprotect(w), "")

    def test_wrapping_twice_is_a_no_op(self):
        from app import secrets_at_rest as sar
        with _EnvKey(KEY_A):
            w = sar.protect("sk-proj-ONCE-abcdefghijklmn")
            self.assertEqual(sar.protect(w), w)

    def test_a_plaintext_key_from_before_this_passes_through(self):
        """Upgrade path: an untagged value is a pre-2026-08-23 credential
        and must keep working until the boot migration rewraps it."""
        from app import secrets_at_rest as sar
        with _EnvKey(KEY_A):
            self.assertEqual(sar.unprotect("sk-legacy-plain-abcdefghijkl"),
                             "sk-legacy-plain-abcdefghijkl")

    def test_empty_stays_empty(self):
        from app import secrets_at_rest as sar
        with _EnvKey(KEY_A):
            self.assertEqual(sar.protect(""), "")
            self.assertEqual(sar.unprotect(""), "")

    def test_a_failed_wrap_never_loses_the_credential(self):
        """The user pasted it. Storing it readable beats refusing to store
        it — this must degrade, never drop."""
        from app import secrets_at_rest as sar
        with _EnvKey("not-a-valid-base64-key-of-the-right-length!!"):
            self.assertEqual(sar.scheme() in ("dpapi", "none"), True)


class ItNeverOverstatesWhatItDid(unittest.TestCase):
    def test_status_reports_plaintext_as_plaintext(self):
        """A false green here is worse than a stated gap: it is the
        sentence someone quotes back later."""
        from app import secrets_at_rest as sar
        with _EnvKey(None):
            if sar._dpapi_available():
                self.skipTest("DPAPI is available on this platform")
            st = sar.status()
            self.assertFalse(st["wrapped"])
            self.assertEqual(st["scheme"], "none")
            self.assertIn("plain text", st["at_rest"].lower())

    def test_status_names_the_scheme_in_plain_words(self):
        from app import secrets_at_rest as sar
        with _EnvKey(KEY_A):
            st = sar.status()
            self.assertTrue(st["wrapped"])
            self.assertEqual(st["scheme"], "key")
            self.assertIn("outside the storage volume", st["at_rest"])

    def test_the_settings_route_publishes_it(self):
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        self.assertIn('"secrets_at_rest": secrets_at_rest.status()', main)

    def test_no_claim_that_the_operator_cannot_read_a_hosted_key(self):
        """Ruled 2026-08-23. Encryption whose key we also hold is not a
        defence against us, and writing otherwise would be the one
        genuinely dishonest sentence available here."""
        src = (ROOT / "app/secrets_at_rest.py").read_text(encoding="utf-8").lower()
        for forbidden in ("we cannot read", "only you can read",
                          "zero knowledge", "zero-knowledge"):
            self.assertNotIn(forbidden, src)


class TheSettingsFileIsWrappedOnDisk(unittest.TestCase):
    def setUp(self):
        from app import paths
        self.tmp = tempfile.TemporaryDirectory()
        home = Path(self.tmp.name)
        self._old = (paths.HOME, paths.SETTINGS)
        paths.HOME, paths.SETTINGS = home, home / "settings.json"
        self.env = _EnvKey(KEY_A)
        self.env.__enter__()

    def tearDown(self):
        from app import paths
        self.env.__exit__()
        paths.HOME, paths.SETTINGS = self._old
        self.tmp.cleanup()

    def _disk(self) -> str:
        from app import paths
        return paths.SETTINGS.read_text(encoding="utf-8")

    def test_every_credential_shape_is_wrapped(self):
        from app import generate
        generate.save_settings({
            "openai_api_key": "sk-OPENAI-abcdefghijklmno",
            "gemini_api_key": "sk-GEMINI-abcdefghijklmno",
            "anthropic_api_key": "sk-ANTHROPIC-abcdefghijk",
            "custom_engines": [{"id": "e", "api_key": "sk-ENGINE-abcdefghijklmn"}],
        })
        raw = self._disk()
        for probe in ("sk-OPENAI", "sk-GEMINI", "sk-ANTHROPIC", "sk-ENGINE"):
            self.assertNotIn(probe, raw, probe)

    def test_a_custom_engines_key_is_not_forgotten(self):
        """It was the likelier leak in the audit — user-supplied base_url,
        so the endpoint holding it is not one we chose."""
        from app import generate
        generate.save_settings({"custom_engines": [
            {"id": "e", "api_key": "sk-ENGINEONLY-abcdefghij"}]})
        self.assertNotIn("sk-ENGINEONLY", self._disk())
        back = generate.load_settings()
        self.assertEqual(back["custom_engines"][0]["api_key"],
                         "sk-ENGINEONLY-abcdefghij")

    def test_non_secrets_stay_readable(self):
        """The file must remain diagnosable. Encrypting the whole thing
        would hide the preferences that explain a support question."""
        from app import generate
        generate.save_settings({"preferred_provider": "openai",
                                "openai_api_key": "sk-X-abcdefghijklmnop"})
        self.assertIn("preferred_provider", self._disk())
        self.assertIn("openai", self._disk())

    def test_callers_keep_seeing_plain_values(self):
        """save_settings deep-copies. Wrapping in place handed one caller
        ciphertext as a key."""
        from app import generate
        d = {"openai_api_key": "sk-CALLER-abcdefghijklmn"}
        generate.save_settings(d)
        self.assertEqual(d["openai_api_key"], "sk-CALLER-abcdefghijklmn")

    def test_a_corrupt_file_still_does_not_brick_the_app(self):
        from app import generate, paths
        paths.SETTINGS.write_text("{not json", encoding="utf-8")
        self.assertEqual(generate.load_settings(), {})

    def test_the_boot_migration_wraps_a_legacy_plaintext_file(self):
        from app import generate, paths
        paths.SETTINGS.write_text(
            json.dumps({"openai_api_key": "sk-LEGACY-abcdefghijklmn"}),
            encoding="utf-8")
        self.assertIn("sk-LEGACY", self._disk())
        r = generate.rewrap_settings_at_rest()
        self.assertEqual(r["rewrapped"], 1)
        self.assertNotIn("sk-LEGACY", self._disk())
        self.assertEqual(generate.load_settings()["openai_api_key"],
                         "sk-LEGACY-abcdefghijklmn")

    def test_the_migration_is_idempotent(self):
        """It runs on every boot. A second pass must do nothing rather than
        re-wrap the wrapper."""
        from app import generate, paths
        paths.SETTINGS.write_text(
            json.dumps({"openai_api_key": "sk-ONCE-abcdefghijklmnop"}),
            encoding="utf-8")
        generate.rewrap_settings_at_rest()
        after_first = self._disk()
        self.assertEqual(generate.rewrap_settings_at_rest()["rewrapped"], 0)
        self.assertEqual(self._disk(), after_first)

    def test_it_runs_at_boot_and_is_not_a_button(self):
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        i = main.index("def _wrap_credentials_at_rest")
        self.assertIn('@app.on_event("startup")', main[max(0, i - 200):i])
        self.assertNotIn("/api/settings/rewrap", main)


class TheTenantKeyLivesOffTheVolume(unittest.TestCase):
    PROV = (ROOT / "storefront/app/provisioner.py").read_text(encoding="utf-8")
    DB = (ROOT / "storefront/app/db.py").read_text(encoding="utf-8")

    def test_each_studio_gets_its_own_key_as_a_railway_variable(self):
        self.assertIn('"SCREENBOARD_SECRET_KEY": ws.secret_key', self.PROV)

    def test_the_key_is_persisted_not_regenerated(self):
        """Regenerating on each provision would orphan every credential the
        studio already holds."""
        self.assertIn("if not ws.secret_key:", self.PROV)
        self.assertIn("secret_key: Mapped[str]", self.DB)

    def test_old_workspaces_get_the_column(self):
        self.assertIn("ALTER TABLE workspaces ADD COLUMN secret_key", self.DB)

    def test_a_generated_key_is_a_valid_aes_length(self):
        import secrets as pysecrets
        t = pysecrets.token_urlsafe(32)
        d = base64.urlsafe_b64decode(t + "=" * (-len(t) % 4))
        self.assertIn(len(d), (16, 24, 32))


if __name__ == "__main__":
    unittest.main()

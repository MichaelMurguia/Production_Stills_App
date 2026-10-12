"""Storefront tests never touch the network.

reconcile() probes an ACTIVE studio's branded address over real HTTPS
(provisioner._domain_serves). Fourteen test files reach reconcile and only
two stubbed the probe, so the suite's outcome depended on the network it ran
on: on 2026-10-11 the connect stalled and the suite hung for good.

Every test file imports this first (test_offline_guard enforces it). It is
not tests/__init__.py because `discover -s tests` never imports the package.
A test that checks the probe's effect swaps in its own answer, as
test_accounts and test_audit_fixes do.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import provisioner  # noqa: E402

provisioner._domain_serves = lambda domain: False

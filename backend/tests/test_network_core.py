"""The network gate and access log's pure core (S013 § 8 Pure)."""

import ipaddress

import pytest

from network_core import (
    DEFAULT_INTERNAL_NETWORKS, SightingCache, classify_outcome, format_networks, gate_refuses, is_internal,
    parse_networks, sighting_hash, truncate,
)

NETS, _ = parse_networks("10.24.0.0/16, 2001:db8::/32")


class TestParseNetworks:

    def test_ipv4_and_ipv6(self):
        networks, error = parse_networks("10.24.0.0/16,2001:db8::/32")
        assert error is None
        assert networks == [ipaddress.ip_network("10.24.0.0/16"), ipaddress.ip_network("2001:db8::/32")]

    def test_spaces_newlines_and_empty_entries(self):
        networks, error = parse_networks("  10.24.0.0/16 ,\r\n192.168.1.0/24\n\n,")
        assert error is None
        assert format_networks(networks) == "10.24.0.0/16,192.168.1.0/24"

    def test_host_bits_are_dropped(self):
        assert format_networks(parse_networks("10.24.0.5/16")[0]) == "10.24.0.0/16"

    def test_a_single_address_is_a_host_range(self):
        assert format_networks(parse_networks("10.24.0.5")[0]) == "10.24.0.5/32"

    @pytest.mark.parametrize("text", ["", "  ", ",\n,", None])
    def test_empty(self, text):
        assert parse_networks(text) == ([], "At least one range is needed")

    def test_a_bad_entry_is_named(self):
        networks, error = parse_networks("10.24.0.0/16, 10.300.0.0/16")
        assert networks == []
        assert "'10.300.0.0/16'" in error

    def test_the_default_parses(self):
        networks, error = parse_networks(DEFAULT_INTERNAL_NETWORKS)
        assert error is None and len(networks) == 3


class TestIsInternal:

    @pytest.mark.parametrize("ip, expected", [
        ("10.24.3.7", True),
        ("10.25.0.1", False),
        ("203.0.113.7", False),
        ("2001:db8::5", True),
        ("2001:db9::5", False),
        ("::ffff:10.24.0.5", True),      # IPv4-mapped IPv6 is unwrapped
        ("::ffff:203.0.113.7", False),
        ("127.0.0.1", True),             # loopback is internal in code, not through the list
        ("127.8.8.8", True),
        ("::1", True),
        (" 10.24.3.7 ", True),
    ])
    def test_classification(self, ip, expected):
        assert is_internal(ip, NETS) is expected

    @pytest.mark.parametrize("ip", ["", None, "not-an-ip", "10.24.0.0/16", "999.1.1.1"])
    def test_unparsable_is_external(self, ip):
        assert is_internal(ip, NETS) is False

    def test_carrier_grade_nat_is_external_by_default(self):
        assert is_internal("100.64.1.1", parse_networks(DEFAULT_INTERNAL_NETWORKS)[0]) is False


class TestGateRefuses:

    @pytest.mark.parametrize("roles, refused", [
        (["it_admin"], True),
        (["it_admin", "maintenance_team"], True),
        (["maintenance_team"], False),           # a manager or engineer: site roles are not in the token
        (["maint_manager"], False),
        (["maint_engineer"], False),
        ([], False),
        (["admin"], False),
    ])
    def test_external(self, roles, refused):
        assert gate_refuses(roles, internal=False) is refused

    @pytest.mark.parametrize("roles", [["it_admin"], ["it_admin", "maintenance_team"], []])
    def test_internal_always_passes(self, roles):
        assert gate_refuses(roles, internal=True) is False


class TestClassifyOutcome:

    def test_a_gate_mark_wins(self):
        assert classify_outcome(403, "denied_network", None, "x") == ("denied_network", None)
        assert classify_outcome(401, "auth_failed", "no_token", None) == ("auth_failed", "no_token")
        assert classify_outcome(403, "denied_perm", "equipment:edit@site:3", "x") == (
            "denied_perm", "equipment:edit@site:3")

    def test_bare_401(self):
        assert classify_outcome(401, None, None, "Unauthorized") == ("auth_failed", None)

    def test_bare_403_keeps_the_start_of_the_message(self):
        assert classify_outcome(403, None, None, "You can't change your own access") == (
            "denied_perm", "You can't change your own access")
        assert classify_outcome(403, None, None, "x" * 300)[1] == "x" * 100
        assert classify_outcome(403, None, None, None) == ("denied_perm", None)

    @pytest.mark.parametrize("status", [200, 201, 400, 404, 409, 500, 503])
    def test_other_statuses_are_ok(self, status):
        assert classify_outcome(status, None, None, "boom") == ("ok", None)


def test_truncate():
    assert truncate(None, 5) is None
    assert truncate("abcdefg", 5) == "abcde"
    assert truncate("abc", 5) == "abc"


class TestSightingHash:
    """S013 A1: the hash half of access_log's one-row-per-sighting-per-day key."""

    KEY = ("ok", "sess-1", "10.0.0.5", None)

    def test_stable_and_forty_hex_characters(self):
        value = sighting_hash(*self.KEY)
        assert value == sighting_hash(*self.KEY)
        # SHA-1 of "ok\x1fsess-1\x1f10.0.0.5\x1f": the same in every process and Python run
        # (unlike hash()), so the key agrees across Gunicorn workers
        assert value == "e1b64e7e920b5cea02040760d5bf5a3d58f78bb1"

    def test_none_and_empty_hash_alike(self):
        assert sighting_hash("ok", "sess-1", "10.0.0.5", None) == sighting_hash("ok", "sess-1", "10.0.0.5", "")
        assert (sighting_hash("auth_failed", None, "10.0.0.5", "no_token")
                == sighting_hash("auth_failed", "", "10.0.0.5", "no_token"))

    @pytest.mark.parametrize("index, other", [
        (0, "denied_perm"), (1, "sess-2"), (2, "203.0.113.5"), (3, "equipment:edit"),
    ])
    def test_each_part_counts(self, index, other):
        changed = list(self.KEY)
        changed[index] = other
        assert sighting_hash(*changed) != sighting_hash(*self.KEY)

    def test_parts_do_not_run_together(self):
        assert sighting_hash("ok", "ab", "c", None) != sighting_hash("ok", "a", "bc", None)


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class TestSightingCache:

    def _cache(self, **kwargs):
        clock = _Clock()
        return SightingCache(600, clock=clock, **kwargs), clock

    def test_first_sighting_then_repeat_suppressed(self):
        cache, _ = self._cache()
        key = ("ok", "sid1", "10.0.0.5", None)
        assert not cache.seen(key)
        cache.remember(key)
        assert cache.seen(key)

    def test_written_again_after_the_window(self):
        cache, clock = self._cache()
        key = ("ok", "sid1", "10.0.0.5", None)
        cache.remember(key)
        clock.now += 599
        assert cache.seen(key)
        clock.now += 1
        assert not cache.seen(key)

    def test_a_new_address_is_a_new_sighting(self):
        cache, _ = self._cache()
        cache.remember(("ok", "sid1", "10.0.0.5", None))
        assert not cache.seen(("ok", "sid1", "203.0.113.7", None))

    def test_not_remembered_means_not_seen(self):
        # The shell remembers only after a successful insert: a failed one is retried
        cache, _ = self._cache()
        assert not cache.seen(("ok", "sid1", "10.0.0.5", None))
        assert not cache.seen(("ok", "sid1", "10.0.0.5", None))

    def test_pruning_drops_expired_then_oldest(self):
        cache, clock = self._cache(max_entries=3)
        cache.remember("a")
        clock.now += 700            # "a" has expired
        cache.remember("b")
        cache.remember("c")
        cache.remember("d")         # four entries: "a" goes
        assert len(cache) == 3 and not cache.seen("a")
        cache.remember("e")         # none expired: the oldest ("b") goes
        assert len(cache) == 3 and not cache.seen("b") and cache.seen("e")

    def test_clear(self):
        cache, _ = self._cache()
        cache.remember("a")
        cache.clear()
        assert not cache.seen("a") and len(cache) == 0

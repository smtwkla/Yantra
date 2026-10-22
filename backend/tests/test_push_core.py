"""push_core — the address check, the endpoint hash, the device label and the push service's
answers (S021 § 5.1, § 5.4, § 8 Pure)."""

import hashlib

import pytest

from push_core import (
    GONE, REFUSED, RETRY, RETRY_LATER, SENT, UNKNOWN_DEVICE, device_label, endpoint_hash, is_endpoint_hash,
    parse_retry_after, push_data, refused_host, send_outcome, send_task_payload, validate_subscription,
)


class TestAddressCheck:

    @pytest.mark.parametrize("endpoint", [
        "https://fcm.googleapis.com/fcm/send/abc:APA91b",
        "https://web.push.apple.com/QGuQyavXutnMH",
        "https://updates.push.services.mozilla.com/wpush/v2/gAAAA",
        "https://wns2-par02p.notify.windows.com/w/?token=BQYAAA",
        "https://FCM.googleapis.com/fcm/send/abc",
    ])
    def test_each_push_service_and_a_sub_domain_pass(self, endpoint):
        assert refused_host(endpoint) is None

    @pytest.mark.parametrize("endpoint, host", [
        ("http://fcm.googleapis.com/fcm/send/abc", "fcm.googleapis.com"),          # not HTTPS
        ("https://10.24.0.5/push", "10.24.0.5"),                                   # an IP
        ("https://fcm.googleapis.com.evil.example/x", "fcm.googleapis.com.evil.example"),  # look-alike
        ("https://evilfcm.googleapis.com.example/x", "evilfcm.googleapis.com.example"),
        ("https://notfcm.googleapis.com/x", "notfcm.googleapis.com"),              # not a sub-domain
        ("https://fcm.googleapis.com:8443/x", "fcm.googleapis.com"),               # a port
        ("https://fcm.googleapis.com:443/x", "fcm.googleapis.com"),                # even the default one
        ("https://user:pw@fcm.googleapis.com/x", "fcm.googleapis.com"),            # user-info
        ("https://internal.example/push", "internal.example"),
    ])
    def test_refused_addresses_name_their_host(self, endpoint, host):
        assert refused_host(endpoint) == host

    # CR1-01: addresses where urlsplit and urllib3 (the parser requests posts with) could find
    # different hosts, or where the host is not a bare DNS name
    @pytest.mark.parametrize("endpoint, host", [
        # urllib3 ends the host at a backslash: requests would post to evil.example / 10.24.0.10
        ("https://evil.example\\.fcm.googleapis.com/x", "evil.example\\.fcm.googleapis.com"),
        ("https://10.24.0.10\\.fcm.googleapis.com/", "10.24.0.10\\.fcm.googleapis.com"),
        ("https:\\\\evil.example/.fcm.googleapis.com", ""),
        # percent-encoding in the authority
        ("https://evil.example%2f.fcm.googleapis.com/x", "evil.example%2f.fcm.googleapis.com"),
        ("https://fcm%2egoogleapis.com/x", "fcm%2egoogleapis.com"),
        # user-info, either side
        ("https://evil.example@fcm.googleapis.com/x", "fcm.googleapis.com"),
        ("https://fcm.googleapis.com@evil.example/x", "evil.example"),
        # a trailing dot
        ("https://fcm.googleapis.com./x", "fcm.googleapis.com."),
        # upper case is read as lower case, so a look-alike stays a look-alike
        ("https://FCM.GOOGLEAPIS.COM.EVIL.EXAMPLE/x", "fcm.googleapis.com.evil.example"),
        # IP literals
        ("https://127.0.0.1/x", "127.0.0.1"),
        ("https://[::1]/x", "::1"),
        ("https://[2001:db8::1]/fcm.googleapis.com", "2001:db8::1"),
        # whitespace and control characters: urlsplit drops a tab or newline silently
        ("https://fcm.googleapis.com /x", "fcm.googleapis.com "),
        ("https://evil\n.fcm.googleapis.com/x", "evil.fcm.googleapis.com"),
        ("https://fcm.googleapis.com/x\ty", "fcm.googleapis.com"),
        # non-ASCII (an ideographic full stop)
        ("https://fcm.googleapis.com。evil.example/x", "fcm.googleapis.com。evil.example"),
        # an empty port
        ("https://fcm.googleapis.com:/x", "fcm.googleapis.com"),
    ])
    def test_parser_tricks_are_refused(self, endpoint, host):
        assert refused_host(endpoint) == host

    @pytest.mark.parametrize("endpoint", [
        "https://wns2-par02p.notify.windows.com/w/?token=BQYAAAD%2bw%3d",   # WNS tokens are URL-encoded
        "https://fcm.googleapis.com/fcm/send/abc#@evil.example/",          # "@" after the authority
    ])
    def test_percent_encoding_and_at_outside_the_authority_pass(self, endpoint):
        assert refused_host(endpoint) is None

    @pytest.mark.parametrize("endpoint", [None, 5, "", " https://fcm.googleapis.com/x", "not a url",
                                          "https://fcm.googleapis.com/" + "a" * 1000])
    def test_no_address_is_refused_with_an_empty_host(self, endpoint):
        assert refused_host(endpoint) == ""


class TestEndpointHash:

    def test_lowercase_hex_sha256(self):
        endpoint = "https://fcm.googleapis.com/fcm/send/abc"
        digest = endpoint_hash(endpoint)
        assert digest == hashlib.sha256(endpoint.encode()).hexdigest()
        assert is_endpoint_hash(digest)

    @pytest.mark.parametrize("text", [None, "", "abc", "A" * 64, "g" * 64, "a" * 63, "a" * 65])
    def test_anything_else_is_not_a_hash(self, text):
        assert not is_endpoint_hash(text)


class TestSubscriptionBody:

    def test_the_browsers_shape(self):
        clean, errors = validate_subscription({"endpoint": "https://x", "keys": {"p256dh": "BNc_x-1", "auth": "tB4="}})
        assert errors == []
        assert clean == {"endpoint": "https://x", "p256dh": "BNc_x-1", "auth": "tB4="}

    @pytest.mark.parametrize("body", [
        {}, {"endpoint": "https://x"}, {"endpoint": "https://x", "keys": []},
        {"endpoint": "https://x", "keys": {"p256dh": "", "auth": "a"}},
        {"endpoint": "https://x", "keys": {"p256dh": "a b", "auth": "a"}},
        {"endpoint": "https://x", "keys": {"p256dh": "a", "auth": "a" * 101}},
        {"endpoint": 5, "keys": {"p256dh": "a", "auth": "a"}},
    ])
    def test_refused(self, body):
        _clean, errors = validate_subscription(body)
        assert errors and "cannot use" in errors[0]["message"]


class TestDeviceLabel:

    @pytest.mark.parametrize("user_agent, label", [
        ("Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/130.0.0.0 Mobile Safari/537.36", "Android · Chrome"),
        ("Mozilla/5.0 (Linux; Android 14; SAMSUNG SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) "
         "SamsungBrowser/26.0 Chrome/122.0.0.0 Mobile Safari/537.36", "Android · Samsung Internet"),
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
         "Version/18.0 Mobile/15E148 Safari/604.1", "iPhone · Safari"),
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
         "Mobile/15E148", "iPhone"),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0", "Windows · Edge"),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0", "Windows · Firefox"),
        ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/130.0.0.0 Safari/537.36", "Mac · Chrome"),
    ])
    def test_real_user_agents(self, user_agent, label):
        assert device_label(user_agent) == label

    @pytest.mark.parametrize("user_agent", [None, "", "curl/8.4.0"])
    def test_nothing_known_is_an_unknown_device(self, user_agent):
        assert device_label(user_agent) == UNKNOWN_DEVICE


class TestSendOutcome:

    @pytest.mark.parametrize("status, outcome", [
        (201, (SENT, None)), (202, (SENT, None)),
        (404, (GONE, None)), (410, (GONE, None)),
        (400, (REFUSED, None)), (403, (REFUSED, None)), (413, (REFUSED, None)),
        (503, (RETRY, None)), (500, (RETRY, None)),
    ])
    def test_status(self, status, outcome):
        assert send_outcome(status, None) == outcome

    def test_429_with_retry_after_waits_that_long(self):
        assert send_outcome(429, "120") == (RETRY_LATER, 120)

    @pytest.mark.parametrize("retry_after", [None, "", "Wed, 21 Oct 2026 07:28:00 GMT", "1.5", "-3", "١٢"])
    def test_429_without_a_whole_number_uses_the_back_off(self, retry_after):
        assert send_outcome(429, retry_after) == (RETRY, None)

    def test_retry_after_parse(self):
        assert parse_retry_after(" 30 ") == 30
        assert parse_retry_after("Wed, 21 Oct 2026 07:28:00 GMT") is None


class TestPayloads:

    def test_quiet_alert_goes_low_and_silent(self):
        message = {"title": "Defect · S.U · M", "body": "b", "path": "/tickets/5", "tag": "ticket-5", "quiet": True}
        payload = send_task_payload(7, message, 3600)
        assert payload == {"subscription_id": 7, "title": "Defect · S.U · M", "body": "b", "path": "/tickets/5",
                           "tag": "ticket-5", "urgency": "low", "silent": True, "ttl": 3600}
        assert push_data(payload) == {"title": "Defect · S.U · M", "body": "b", "path": "/tickets/5",
                                      "tag": "ticket-5", "silent": True}

    def test_normal_alert_goes_high(self):
        message = {"title": "t", "body": "b", "path": "/", "tag": "x", "quiet": False}
        payload = send_task_payload(1, message, 300)
        assert payload["urgency"] == "high" and payload["silent"] is False and payload["ttl"] == 300

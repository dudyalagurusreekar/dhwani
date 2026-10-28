"""
Dhwani / EchoShield AI - SSRF & External URL Defense Engine
===========================================================
Defends against Server-Side Request Forgery by inspecting URL schemes,
resolving hostnames, and blocking private, loopback, link-local, and cloud metadata IPs.
"""

import ipaddress
import socket
from typing import List, Optional, Set, Tuple
from urllib.parse import urlparse


BLOCKED_HOSTNAMES: Set[str] = {
    "localhost",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # IPv4 loopback
    ipaddress.ip_network("10.0.0.0/8"),       # IPv4 private
    ipaddress.ip_network("172.16.0.0/12"),    # IPv4 private
    ipaddress.ip_network("192.168.0.0/16"),   # IPv4 private
    ipaddress.ip_network("169.254.0.0/16"),   # IPv4 link-local & cloud metadata
    ipaddress.ip_network("100.64.0.0/10"),    # Carrier-Grade NAT (RFC 6598)
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 private (ULA)
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
]


class SSRFSecurityError(Exception):
    """Raised when a URL violates SSRF security policies."""
    pass


def is_ip_blocked(ip_addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address belongs to blocked or private ranges."""
    if ip_addr.is_loopback or ip_addr.is_private or ip_addr.is_link_local or ip_addr.is_reserved or ip_addr.is_multicast:
        return True
    return any(ip_addr in net for net in BLOCKED_IP_NETWORKS)


def is_ip_allowed(ip_str: str) -> bool:
    """Return True if IP is permitted (public routable), False if blocked."""
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        return not is_ip_blocked(ip)
    except ValueError:
        return False


def validate_url_security(
    url: str,
    allowed_domains: Optional[List[str]] = None,
    allow_private_in_dev: bool = False,
    only_youtube: bool = False,
    raise_on_error: bool = False,
) -> Tuple[bool, str]:
    """
    Validate that an external URL does not target internal, loopback, or metadata services.

    Args:
        url: The external URL to validate.
        allowed_domains: Optional whitelist of permitted domain suffixes (e.g. ['youtube.com', 'youtu.be']).
        allow_private_in_dev: If True, bypasses private IP blocking (disabled by default).
        only_youtube: Shorthand to enforce YouTube-only domain whitelist.
        raise_on_error: If True, raises SSRFSecurityError instead of returning (False, reason).

    Returns:
        (is_safe: bool, reason: str)
    """
    if only_youtube:
        allowed_domains = ["youtube.com", "youtu.be"]

    def _fail(msg: str) -> Tuple[bool, str]:
        if raise_on_error:
            raise SSRFSecurityError(msg)
        return False, msg

    if not url or not isinstance(url, str):
        return _fail("URL cannot be empty.")

    try:
        parsed = urlparse(url.strip())
    except Exception as exc:
        return _fail(f"Malformed URL syntax: {exc}")

    # 1. Scheme validation (only http and https)
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return _fail(f"Scheme '{scheme}' not allowed. Only HTTP and HTTPS are permitted.")

    # 2. Reject credentials in URL (e.g. https://user:pass@evil.com)
    if parsed.username or parsed.password:
        return _fail("URLs containing embedded authentication credentials are not permitted.")

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return _fail("URL must contain a valid hostname.")

    # 3. Check blocked hostnames
    if hostname in BLOCKED_HOSTNAMES:
        return _fail(f"Blocked SSRF target host '{hostname}'.")

    # 4. Check domain whitelist if specified
    if allowed_domains:
        domain_match = False
        for dom in allowed_domains:
            norm_dom = dom.lower().lstrip(".")
            if hostname == norm_dom or hostname.endswith(f".{norm_dom}"):
                domain_match = True
                break
        if not domain_match:
            return _fail(f"Host '{hostname}' is not an allowed YouTube domain: {allowed_domains}")

    # 5. IP Address and DNS resolution verification
    if not allow_private_in_dev:
        try:
            # Check if hostname is an explicit IP address
            ip_obj = ipaddress.ip_address(hostname)
            if is_ip_blocked(ip_obj):
                return _fail(f"Blocked SSRF target IP address '{hostname}'.")
        except ValueError:
            # Hostname is a domain name -> resolve via DNS to inspect all destination IPs
            try:
                addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
                for entry in addr_info:
                    sockaddr = entry[4]
                    ip_str = sockaddr[0]
                    resolved_ip = ipaddress.ip_address(ip_str)
                    if is_ip_blocked(resolved_ip):
                        return _fail(f"Blocked SSRF target IP: host '{hostname}' resolves to private/restricted IP '{ip_str}'.")
            except socket.gaierror as dns_err:
                return _fail(f"Failed to resolve host '{hostname}': {dns_err}")

    return True, "URL passed security verification."


# Bugfix Requirements Document

## Introduction

This document addresses the VPN connectivity failure caused by a mismatch between Reality configuration serverNames and the SNI values used in generated VPN URLs. The bug prevents the CDN bypass configuration from working, resulting in users receiving only one functional server instead of two separate working servers (Direct + CDN Bypass).

**Impact**: Users cannot connect via CDN bypass configuration, limiting their ability to circumvent network blocks. The ping shows N/A for connections, indicating failed validation.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the Reality configuration serverNames array contains only ["www.google.com", "google.com"] AND the VPN service generates a vless:// URL with sni=djanvpn.ru for CDN bypass THEN the system fails to validate the connection and shows N/A ping status

1.2 WHEN users attempt to add the CDN bypass server configuration with SNI djanvpn.ru THEN the system rejects the connection because djanvpn.ru is not in the Reality serverNames whitelist

1.3 WHEN the VPN service creates dual configurations THEN the system only successfully adds one server (Direct VPN) instead of two separate working servers

### Expected Behavior (Correct)

2.1 WHEN the Reality configuration serverNames array includes djanvpn.ru AND the VPN service generates a vless:// URL with sni=djanvpn.ru for CDN bypass THEN the system SHALL successfully validate the connection and show proper connectivity status

2.2 WHEN users attempt to add the CDN bypass server configuration with SNI djanvpn.ru THEN the system SHALL accept the connection and establish a working VPN tunnel through Cloudflare CDN

2.3 WHEN the VPN service creates dual configurations THEN the system SHALL successfully add two separate working servers: "⚡ | 🇳🇱 Netherlands VPN" (Direct via IP with SNI www.google.com) and "⚡ | 🇳🇱 Netherlands Обход" (CDN bypass via djanvpn.ru with SNI djanvpn.ru)

### Unchanged Behavior (Regression Prevention)

3.1 WHEN users connect to the Direct VPN server with SNI www.google.com or google.com THEN the system SHALL CONTINUE TO establish successful connections with proper connectivity status

3.2 WHEN the Reality configuration processes connections with serverNames www.google.com or google.com THEN the system SHALL CONTINUE TO validate and accept these connections without any changes to existing behavior

3.3 WHEN the VPN service generates vless:// URLs with existing Reality parameters (pbk, fp, sid, spx, flow) THEN the system SHALL CONTINUE TO use the same parameter values for both Direct and CDN bypass configurations

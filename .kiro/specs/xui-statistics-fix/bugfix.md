# Bugfix Requirements Document

## Introduction

The Telegram VPN bot creates clients by directly modifying the x-ui SQLite database (`/etc/x-ui/x-ui.db`), which bypasses x-ui's internal tracking mechanisms. This causes bot-created clients to appear offline with 0 GB traffic usage in the x-ui web interface, even though VPN connections function correctly. Manually created clients (through the web interface) display statistics properly. This bug prevents administrators from monitoring bot-created client usage and connection status through the x-ui dashboard.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a client is created via the bot's `_create_user_sync()` method using direct database manipulation THEN the client appears in the x-ui web interface but shows as "offline" regardless of actual connection status

1.2 WHEN a bot-created client connects to the VPN and transfers data THEN the traffic usage remains at 0 GB in the x-ui web interface

1.3 WHEN the bot deletes a client via `_delete_user_sync()` using direct database manipulation THEN x-ui's internal state/cache is not updated, potentially causing stale data

### Expected Behavior (Correct)

2.1 WHEN a client is created via the bot THEN the client SHALL appear in the x-ui web interface with proper tracking enabled, showing online status when connected

2.2 WHEN a bot-created client connects to the VPN and transfers data THEN the traffic usage SHALL be tracked and displayed in real-time in the x-ui web interface (GB downloaded/uploaded)

2.3 WHEN the bot deletes a client THEN x-ui's internal state SHALL be properly updated and the client SHALL be removed from all tracking mechanisms

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a client is created via the bot THEN the VPN connection SHALL CONTINUE TO work correctly with VLESS-Reality-TCP-Vision protocol

3.2 WHEN a client subscription URL is generated THEN it SHALL CONTINUE TO contain the correct Reality parameters (pbk, fp, sni, sid, spx, flow)

3.3 WHEN the bot creates or deletes clients THEN existing VPN connections for other clients SHALL CONTINUE TO function without interruption

3.4 WHEN manually created clients (through x-ui web interface) exist THEN they SHALL CONTINUE TO show statistics correctly

3.5 WHEN the bot operates in mock mode (`VPN_MOCK_MODE=True`) THEN it SHALL CONTINUE TO function for testing without requiring a real VPN panel

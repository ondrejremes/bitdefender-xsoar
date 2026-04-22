# Bitdefender GravityZone

This pack integrates with **Bitdefender GravityZone** security platform, enabling endpoint management and automated response to security events.

## What does this pack do?

- Receives push events from GravityZone via the generic webhook integration and classifies them into typed incidents (malware detections, EDR/XDR incidents, network events, system events).
- Provides commands to manage endpoints: list, inspect, isolate, and de-isolate.
- Creates and monitors scan tasks.
- Manages EDR/XDR incident notes and statuses.
- Manages the network blocklist (hash, path, connection rules).
- Lists and manages quarantined items.
- Configures and tests GravityZone push event notification settings.

## Pack Contents

### Integrations

| Integration | Description |
|---|---|
| Bitdefender GravityZone API | Communicates with the GravityZone Public API (JSON-RPC 2.0). |

### Incident Types

| Type | Module values |
|---|---|
| Bitdefender GravityZone Malware | av, avc, hd, antiexploit, network-sandboxing, ransomware-mitigation |
| Bitdefender GravityZone Exchange Malware | exchange-malware |
| Bitdefender GravityZone EDR Incident | new-incident |
| Bitdefender GravityZone XDR Incident | new-extended-incident |
| Bitdefender GravityZone Network Event | fw, network-monitor, aph, dp, uc |
| Bitdefender GravityZone System Event | modules, sva, registration, install, uninstall, and others |

### Classifiers

- **Bitdefender GravityZone - Classifier**: Classifies incoming webhook events into typed incidents based on the `module` field.
- **Bitdefender GravityZone - Incoming Mapper**: Maps event fields to XSOAR incident fields.

## Configuration

### GravityZone API Integration

1. Navigate to **Settings → Integrations** and search for *Bitdefender GravityZone API*.
2. Enter your **GravityZone Console URL** (e.g. `https://cloud.gravityzone.bitdefender.com`).
3. Enter your **API Key** (from GravityZone → My Account → API keys).
4. Click **Test**.

### Push Event Webhook

GravityZone push events are received via the **Generic Webhook** integration. Configure it to use:

- **Classifier**: Bitdefender GravityZone - Classifier
- **Incoming Mapper**: Bitdefender GravityZone - Incoming Mapper

Then configure the GravityZone push notification URL using the `bd-push-settings-set` command, pointing it to your XSOAR webhook endpoint.

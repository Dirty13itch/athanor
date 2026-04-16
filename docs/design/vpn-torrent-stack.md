# qBittorrent + Gluetun VPN Stack

*Torrent client with mandatory VPN tunnel. Blocked on NordVPN credentials.*

---

## Architecture

Torrent traffic MUST be tunneled through a VPN. Gluetun creates the VPN tunnel and forces all qBittorrent traffic through it. If the VPN drops, qBittorrent loses network access entirely — no IP leak possible.

```yaml
# Docker Compose on VAULT
services:
  gluetun:
    image: qmcgaw/gluetun
    cap_add:
      - NET_ADMIN
    environment:
      - VPN_SERVICE_PROVIDER=nordvpn
      - VPN_TYPE=openvpn  # or wireguard
      - OPENVPN_USER=<nordvpn_service_username>
      - OPENVPN_PASSWORD=<nordvpn_service_password>
      - SERVER_COUNTRIES=Switzerland  # privacy-friendly jurisdiction
    ports:
      - 8112:8112  # qBittorrent web UI (exposed through Gluetun's network)
    restart: unless-stopped

  qbittorrent:
    image: linuxserver/qbittorrent
    network_mode: "service:gluetun"  # ALL traffic goes through Gluetun
    environment:
      - PUID=99
      - PGID=100
      - WEBUI_PORT=8112
    volumes:
      - /mnt/user/data/downloads:/downloads
      - /mnt/user/appdata/qbittorrent:/config
    restart: unless-stopped
```

---

## Kill Switch

`network_mode: "service:gluetun"` means qBittorrent has NO direct network access. If Gluetun's VPN tunnel drops, qBittorrent is fully isolated. This is implemented by Docker networking — no configuration needed beyond the network_mode setting.

---

## Integration with *arr Stack

- Sonarr and Radarr talk to qBittorrent's API through the exposed port (8112)
- They send download requests and monitor completion
- When a download finishes, Sonarr/Radarr hardlink or move the file to the library and trigger a Plex scan

SABnzbd connects directly to Usenet providers over SSL — no VPN needed for Usenet.

---

## Download Pipeline (Complete)

```
Prowlarr (indexer management — aggregates Usenet + torrent indexers)
  ↓ feeds indexers to
Sonarr + Radarr (request management — tracks wanted content, grabs releases)
  ↓ sends downloads to
SABnzbd (Usenet) + qBittorrent/Gluetun (torrent over VPN)
  ↓ completed downloads processed by
Sonarr/Radarr (rename, move to library, update metadata)
  ↓ library changes detected by
Plex (automatic library scan) + Tdarr (transcoding queue)
```

---

## Blocker

**NordVPN service credentials needed.** These are separate from the NordVPN account login — generated in the NordVPN dashboard under "Manual Setup." Shaun needs to provide these.

---

## Ansible Role

Will be added to the VAULT playbook as `vault-vpn-torrent` role once credentials are available. Pattern follows existing media stack roles: Docker API deployment with `restart: unless-stopped`.

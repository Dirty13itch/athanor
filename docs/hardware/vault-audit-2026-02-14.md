# VAULT Audit — 2026-02-14

**Hostname:** Unraid
**Role:** Primary storage and services server
**IP:** 192.168.1.203 (br0, bonded)
**OS:** Unraid 7.2.0 (Slackware 15.0+, kernel 6.12.54-Unraid)
**SSH:** root / password auth + ed25519 key installed

---

## CPU

| Field | Value |
|-------|-------|
| Model | AMD Ryzen Threadripper 7960X |
| Cores | 24 |
| Threads | 48 |
| Base Clock | 4.2 GHz |
| Boost Clock | 5.665 GHz |
| Architecture | Zen 4 (Genoa/Bergamo) |
| L3 Cache | 128 MiB (4 instances) |
| Virtualization | AMD-V |

## Motherboard

| Field | Value |
|-------|-------|
| Manufacturer | Gigabyte Technology Co., Ltd. |
| Model | TRX50 AERO D |
| BIOS | FA3e (American Megatrends, 2025-10-30) |
| Chipset | AMD 600 Series |

## RAM

| Slot | Module | Capacity | Speed |
|------|--------|----------|-------|
| P0 CHANNEL A, DIMM 0 | Kingston KF556R28-32 | 32 GB | DDR5-4800 |
| P0 CHANNEL C, DIMM 0 | Kingston KF556R28-32 | 32 GB | DDR5-4800 |
| P0 CHANNEL E, DIMM 0 | Kingston KF556R28-32 | 32 GB | DDR5-4800 |
| P0 CHANNEL G, DIMM 0 | Kingston KF556R28-32 | 32 GB | DDR5-4800 |
| **Total** | | **128 GB** | |

Note: Kingston KF556R28-32 are DDR5-5600 rated ECC modules running at 4800 MT/s. Quad-channel TRX50 platform.

## GPU

| Field | Value |
|-------|-------|
| Model | Intel Arc A380 (DG2) |
| Type | Discrete GPU |
| Driver | No nvidia-smi (Intel GPU) |

Note: Arc A380 provides hardware transcoding (Quick Sync via Intel oneVPL/VAAPI). Not a compute GPU.

## Storage

### NVMe Drives

| Device | Model | Size | Mount | Filesystem | Usage |
|--------|-------|------|-------|------------|-------|
| nvme0n1 | Crucial P310 (DRAM-less) | 931.5 GB | /mnt/docker | btrfs | Empty |
| nvme1n1 | **Crucial T700** | 3.6 TB | /mnt/appdatacache | btrfs | 761 GB used |
| nvme2n1 | Crucial P310 (DRAM-less) | 931.5 GB | /mnt/transcode | btrfs | Empty |
| nvme3n1 | Crucial P310 (DRAM-less) | 931.5 GB | /mnt/vms | btrfs | Empty |

### HDD Array (Unraid)

| Device | Model | Size | Mount | Used | Free |
|--------|-------|------|-------|------|------|
| sdb | WDC WD241KFGX-68CNGN0 | 21.8 TB | disk9 | 20 TB | 2.8 TB |
| sdc | WDC WD241KFGX-68CNGN0 | 21.8 TB | (parity?) | — | — |
| sdd | WDC WD181KFGX-68AFPN0 | 16.4 TB | disk1 | 15 TB | 1.5 TB |
| sde | ST20000VE002-3G9101 | 18.2 TB | disk2 | 15 TB | 1.8 TB |
| sdf | WDC WD201KFGX-68BKJN0 | 18.2 TB | disk3 | 17 TB | 2.2 TB |
| sdg | WDC WD201KFGX-68BKJN0 | 18.2 TB | disk4 | 17 TB | 1.4 TB |
| sdh | WDC WD201KFGX-68BKJN0 | 18.2 TB | disk5 | 17 TB | 1.4 TB |
| sdi | WDC WD201KFGX-68BKJN0 | 18.2 TB | disk6 | 17 TB | 1.9 TB |
| sdj | WDC WD181KFGX-68AFPN0 | 16.4 TB | disk7 | 16 TB | 2.4 TB |
| sdk | WDC WD201KFGX-68BKJN0 | 18.2 TB | disk8 | 16 TB | 2.8 TB |

**Boot:** SanDisk Cruzer Glide 28.7 GB USB (sda)

### Array Summary

| Metric | Value |
|--------|-------|
| Total array (user share) | 164 TB |
| Used | 146 TB |
| Free | 18 TB |
| Utilization | ~90% |
| Parity drives | 1x 21.8 TB (likely sdc) |
| Data drives | 9 |

### NVMe Summary

| Metric | Value |
|--------|-------|
| Total NVMe | ~6.4 TB |
| Cache (T700) | 3.6 TB (761 GB used) |
| Docker pool | 931 GB (empty) |
| Transcode pool | 931 GB (empty) |
| VM pool | 931 GB (empty) |

## HBA

| Field | Value |
|-------|-------|
| Model | Broadcom/LSI SAS3224 |
| Type | SAS-3 HBA (Fusion-MPT) |

## Network

| Interface | Controller | Speed | Status |
|-----------|-----------|-------|--------|
| eth0 | Aquantia AQC113C | 5GbE NBase-T | DOWN |
| eth1 | Realtek RTL8125 | 2.5GbE | UP (bonded) |
| bond0 | (bond of eth1) | — | UP |
| br0 | Bridge on bond0 | — | 192.168.1.203/24 |
| docker0 | Docker bridge | — | 172.17.0.1/16 |

**Note:** The Aquantia 5GbE NIC is present but DOWN. Connected to the USW Pro XG 10 PoE? Could enable 5GbE if connected.

## Thunderbolt

Intel Thunderbolt 4 (Maple Ridge 4C) controller present with USB controller. Part of TRX50 AERO D motherboard.

## Docker Containers

| Container | Status | Image |
|-----------|--------|-------|
| stash | Up | ghcr.io/hotio/stash:latest |
| stash-maint | Up | alpine:latest |
| stash-jobs | Up | alpine:latest |

## Key Observations

1. **Threadripper 7960X** — This is a current-gen workstation CPU. 24C/48T with AVX-512. Massive compute headroom.
2. **128 GB DDR5 ECC** — Only using 4 channels of the TRX50's available slots. Could expand.
3. **Array is 90% full** — 18 TB free across 164 TB. Will need expansion or cleanup eventually.
4. **5GbE available but unused** — Aquantia AQC113C is present but eth0 is DOWN.
5. **T700 4TB NVMe** — High-performance cache drive (PCIe 5.0). Serious hardware choice.
6. **Arc A380** — Provides hardware video transcoding without consuming a GPU slot for compute.
7. **Only Stash running** — No Plex, no *arr stack visible in Docker. Either not configured or stopped.

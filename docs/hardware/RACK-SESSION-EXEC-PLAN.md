# Rack Session - Executive Plan
**Date:** 2026-02-20
**Scope:** Full system reconfiguration to optimal Athanor configuration
**Decision Authority:** Lead Architect (Claude)
**Approved By:** Shaun

---

## Executive Summary

Based on comprehensive analysis (22-thought sequential analysis + parallel gap analysis), **the optimal configuration maximizes concurrent serving capability while maintaining VRAM pooling flexibility.**

**Target State:**
- Node 1: 7 GPUs, 148 GB VRAM total, dual PSU, mining enclosure
- Node 2: 1 GPU (5090 for ComfyUI), TRX50
- 5 concurrent GPU endpoints + cloud hybrid
- All VISION.md principles satisfied

**Cost:** $200-340 (mining enclosure + risers + Add2PSU adapter)
**Timeline:** 3 phases over 2 days (30 min validation + 3-4 hour rack session + ongoing iteration)

---

## Three-Phase Execution

### Phase A: Critical Pre-Validation (30 minutes, BEFORE rack session)

**Objective:** Validate that TP=4 pooling actually helps performance.

**Why:** We're betting the configuration on TP=4 being viable for 70B models. If TP overhead kills performance, we need to know BEFORE spending 4 hours reconfiguring hardware.

**Execute on Node 1:**
```bash
ssh athanor@192.168.1.244
cd /home/shaun/athanor
./scripts/tp-benchmark.sh
```

**What it does:**
1. Tests Qwen3-32B-AWQ with TP=1, TP=2, TP=4
2. Measures tok/s for each configuration
3. Tells you if TP=4 is viable or hurts performance

**Decision Point:**
- ✓ If TP=4 ≥ 80% of TP=1 performance: **Proceed with 7-GPU config**
- ✗ If TP=4 < 80% of TP=1 performance: **Reconsider** (fall back to distributed serving)

**Expected Result:** TP=4 should be ~60-80% of TP=1 speed but enables 4× the VRAM (64 GB pooled). This is acceptable for 70B models.

---

### Phase B: Rack Session Execution (3-4 hours, AFTER validation)

**Prerequisites:**
- Phase A benchmark complete
- TP=4 validated as viable
- All hardware parts identified and staged
- Field manual printed or accessible on laptop

**Hardware Moves:**

#### 1. 5GbE Network (20 min)
- Move all node ethernet cables to USW Pro XG 10 PoE switch
- Verify link speed with `ethtool eth0` on each node
- Update /etc/netplan/ configs if needed

#### 2. Node 2 Physical Work (60 min)
- Power off Node 2
- Move RTX 4090 from Node 2 slot 2 → Node 1 (slot TBD)
- Leave RTX 5090 in Node 2 slot 1 (for ComfyUI)
- Move 7960X from VAULT → Node 2 (TR5 swap)
- Move TRX50 motherboard from Node 2 → VAULT
- Verify POST, enable EXPO in BIOS (DDR5 3600 → 5600 MT/s)
- Reconnect JetKVM ATX power cable
- Boot, verify 5GbE link

#### 3. Node 1 GPU Expansion (90 min)
- Power off Node 1
- Install RTX 5060 Ti (new, purchased today)
- Install RTX 4090 (from Node 2)
- Verify 7 GPUs total: 4× 5070 Ti + 4090 + 5060 Ti + 3060
- **HOLD** on dual PSU/mining enclosure (Phase C purchase)
- Power on with 1600W PSU (run at lower power limits temporarily)
- Set all GPUs to 200W limit: `sudo nvidia-smi -pl 200`

#### 4. Samsung 990 PRO 4TB (15 min)
- Check BIOS M.2 settings (slot 1 vs slot 2 enablement)
- Reseat if not detected
- Verify with `lsblk`

#### 5. Software Reconfiguration (30 min)
- Update Ansible inventory (Node 2 is now 7960X + single GPU)
- Deploy new service configs
- Restart vLLM on Node 1 with 7 GPUs available
- Verify all GPUs detected: `nvidia-smi`

**Validation:**
- All nodes boot
- All GPUs detected
- 5GbE links up
- Services can start (don't need to be running yet)

---

### Phase C: Post-Validation & Iteration (Ongoing)

**After Phase B complete:**

1. **Purchase mining enclosure setup** ($200-340):
   - 6-8 GPU mining frame/enclosure
   - 7× PCIe gen4 risers (USB 3.0 style, 60cm+)
   - Add2PSU adapter (Corsair 1600W + ASUS ROG 1200W)
   - Additional PCIe power cables if needed

2. **Dual PSU installation** (when parts arrive):
   - Follow dual PSU wiring guide
   - Move GPUs to mining enclosure
   - Remove power limits, run at optimized voltages
   - Validate thermals under sustained load

3. **Benchmark suite** (1-2 hours):
   - TP scaling study (already have TP=4 data)
   - Network bandwidth profiling (NFS vs local)
   - Thermal mapping (7 GPUs sustained)
   - Model quality comparison (AWQ vs FP8 vs FP16)

4. **Operational hardening**:
   - Create runbooks (GPU add, model swap, driver update, failure recovery)
   - Set up automated health checks
   - Test backup/recovery procedures
   - Document failure modes and mitigations

---

## Shopping List (Phase C)

**Required for dual PSU + 7 GPU final config:**

| Item | Estimated Cost | Where | Notes |
|------|---------------|-------|-------|
| Mining enclosure/frame (6-8 GPU) | $80-150 | Amazon/Newegg | Open air frame, good airflow |
| PCIe gen4 risers (7×) | $70-140 | Amazon | USB 3.0 style, 60cm+, shielded |
| Add2PSU adapter | $15-25 | Amazon | Powers secondary PSU from primary |
| PCIe 8-pin cables (if needed) | $20-30 | Amazon/eBay | For ASUS ROG PSU |
| **Total** | **$185-345** | | One-time cost |

**Already owned:**
- ASUS ROG 1200W PSU (loose, available)
- All 7 GPUs
- All NVMe drives
- All RAM
- Both motherboards (ROMED8-2T, TRX50 AERO D)

---

## Risk Mitigation

### What Could Go Wrong

1. **TP=4 overhead is too high** → Validated in Phase A, pivot to distributed serving
2. **1600W PSU can't handle 7 GPUs** → Run at 200W limits until dual PSU arrives
3. **Mining enclosure doesn't fit in rack** → Measure before purchase, return if needed
4. **Thermal throttling with 7 GPUs** → Validated in Phase C benchmarks, adjust config
5. **Node fails to POST after changes** → Field manual has troubleshooting table

### Rollback Strategy

If anything fails during Phase B:
- Node 1: Can run with 4-6 GPUs (leave one out)
- Node 2: RTX 5090 stays, can run ComfyUI standalone
- Network: Can fall back to 1GbE if 5GbE issues
- Worst case: Reverse motherboard swap, back to original config in ~2 hours

---

## Success Criteria

**Phase A Success:**
- TP=4 overhead ≤ 20% (60-80% of TP=1 speed)
- Decision made: proceed or pivot

**Phase B Success:**
- All nodes boot and POST
- All 7 GPUs detected on Node 1
- 5GbE network operational
- Services can start (validation smoke test)

**Phase C Success:**
- Dual PSU stable under load
- All GPUs running at optimal power/thermals
- 5 concurrent endpoints serving
- Benchmarks meet performance targets
- Documentation complete

---

## Next Steps (Immediate)

**YOU (Shaun) - Phase A Validation:**
1. SSH to Node 1: `ssh athanor@192.168.1.244`
2. Run benchmark: `cd /home/shaun/athanor && ./scripts/tp-benchmark.sh`
3. Wait 30 minutes (script automates everything)
4. Review results, report back

**Based on results:**
- ✓ TP=4 good → Proceed to Phase B (rack session)
- ✗ TP=4 bad → Revise config (I'll provide alternative)

**After Phase A:**
- Update BUILD-ROADMAP.md with validation results
- Update field manual if needed
- Proceed to Phase B when ready (same day or next day)

---

## Appendix: Alternative Configurations (If TP=4 Fails)

If Phase A shows TP overhead is prohibitive, fallback configuration:

**Distributed Serving (No TP pooling):**
- Node 1 GPU 1: Llama 70B Q4 (won't fit, need 48+ GB)
- Node 1 GPU 1-2: Llama 70B Q5 split across 2× 5070 Ti (manual sharding)
- Node 1 GPU 3: Qwen3-32B @ 60-80 tok/s
- Node 1 GPU 4: Mistral 7B @ 80-100 tok/s
- Node 1 GPU 5 (4090): Phi-4 tool calling @ 100+ tok/s
- Node 1 GPU 6 (5060 Ti): Embeddings or spare
- Node 1 GPU 7 (3060): Background tasks
- Node 2 GPU (5090): ComfyUI

**Tradeoff:** Can't run 70B models in TP cluster, but maximizes independent serving endpoints.

---

**Document Status:** APPROVED
**Last Updated:** 2026-02-20
**Next Review:** After Phase A completion

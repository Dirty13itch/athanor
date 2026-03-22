#!/usr/bin/env python3
"""
Custom MLP Aesthetic Scorer Trainer
====================================
Trains a personal MLP on top of SigLIP embeddings using images rated in Stash.
Output weights can be loaded by the WORKSHOP scorer service as a drop-in replacement.

Usage:
    python train-custom-scorer.py --check           # dry-run: count available training data
    python train-custom-scorer.py --train           # full training run
    python train-custom-scorer.py --train --epochs 30 --batch-size 32
    python train-custom-scorer.py --evaluate --weights /path/to/weights.pt
    python train-custom-scorer.py --export-embeddings  # cache embeddings to disk for faster retraining
    python train-custom-scorer.py --train --embeddings-cache embeddings.npz

Architecture:
    SigLIP ViT-SO400M-14-SigLIP (1152-dim) → MLP → [0,1] aesthetic score
    Same SigLIP backbone as aesthetic-predictor-v2.5, so embeddings are compatible.
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import requests
import torch
import torch.nn as nn
from io import BytesIO
from PIL import Image
from torch.utils.data import DataLoader, Dataset, random_split
from scipy.stats import spearmanr

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

STASH_URL = os.environ.get("STASH_URL", "http://192.168.1.203:9999")
STASH_API_KEY = os.environ.get("STASH_API_KEY", "")  # blank = no auth
EMBEDDING_DIM = 1152  # SigLIP ViT-SO400M-14-SigLIP output dim
DEFAULT_OUTPUT_DIR = Path("/home/shaun/models/custom-scorer")
DEFAULT_WEIGHTS = DEFAULT_OUTPUT_DIR / "custom_mlp.pt"
DEFAULT_CACHE = DEFAULT_OUTPUT_DIR / "embeddings.npz"
SIGLIP_MODEL_ID = "google/siglip-so400m-patch14-384"

# Rating thresholds (Stash uses 0-100 scale, 5-star = 100, 4-star = 80, etc.)
HIGH_RATING_MIN = 60   # >=60 → positive (3+stars, adjust as library grows)
LOW_RATING_MAX = 40    # <=40 → negative (1-2 stars)

# Training
DEFAULT_EPOCHS = 50
DEFAULT_BATCH = 32
DEFAULT_LR = 1e-3
EARLY_STOP_PATIENCE = 8
MIN_SAMPLES_PER_CLASS = 10   # warn if below this, abort if below 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("custom-scorer")


# ---------------------------------------------------------------------------
# Model definition
# ---------------------------------------------------------------------------

class CustomMLP(nn.Module):
    """
    Personal aesthetic MLP on top of frozen SigLIP embeddings.
    Input: 1152-dim SigLIP CLS token embedding.
    Output: single float in [0, 1] (higher = more aesthetic to Shaun).
    """
    def __init__(self, input_dim: int = EMBEDDING_DIM, dropout: float = 0.1):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.LayerNorm(512),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(512, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x).squeeze(-1)

    def save(self, path: Path, metadata: Optional[dict] = None):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "state_dict": self.state_dict(),
            "input_dim": EMBEDDING_DIM,
            "metadata": metadata or {},
        }
        torch.save(payload, path)
        log.info(f"Weights saved → {path}")

    @classmethod
    def load(cls, path: Path) -> "CustomMLP":
        payload = torch.load(path, map_location="cpu", weights_only=False)
        model = cls(input_dim=payload.get("input_dim", EMBEDDING_DIM))
        model.load_state_dict(payload["state_dict"])
        return model


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

@dataclass
class ScoredImage:
    stash_id: str
    rating100: int       # 0–100 Stash raw rating
    thumbnail_url: str
    label: float         # normalised to [0, 1] for training


class EmbeddingDataset(Dataset):
    def __init__(self, embeddings: np.ndarray, labels: np.ndarray):
        self.X = torch.tensor(embeddings, dtype=torch.float32)
        self.y = torch.tensor(labels, dtype=torch.float32)

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


# ---------------------------------------------------------------------------
# Stash GraphQL client
# ---------------------------------------------------------------------------

class StashClient:
    def __init__(self, url: str = STASH_URL, api_key: str = STASH_API_KEY):
        self.endpoint = f"{url}/graphql"
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["ApiKey"] = api_key
        self.image_base = url

    def _query(self, gql: str, variables: Optional[dict] = None) -> dict:
        payload = {"query": gql}
        if variables:
            payload["variables"] = variables
        resp = requests.post(self.endpoint, headers=self.headers,
                             json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise ValueError(f"GraphQL errors: {data['errors']}")
        return data["data"]

    def count_rated(self) -> dict:
        gql = """
        query {
            high: findImages(image_filter: { rating100: { modifier: GREATER_THAN, value: %d } }) { count }
            low:  findImages(image_filter: { rating100: { modifier: LESS_THAN,    value: %d } }) { count }
            total: findImages { count }
        }
        """ % (HIGH_RATING_MIN - 1, LOW_RATING_MAX + 1)
        data = self._query(gql)
        return {
            "high": data["high"]["count"],
            "low":  data["low"]["count"],
            "total": data["total"]["count"],
        }

    def fetch_rated_images(
        self,
        min_rating: int,
        max_rating: Optional[int] = None,
        page_size: int = 200,
    ) -> list[ScoredImage]:
        """Fetch all images with ratings in [min_rating, max_rating] (both inclusive)."""
        if max_rating is None:
            filter_expr = '{ modifier: GREATER_THAN, value: %d }' % (min_rating - 1)
        else:
            # Use BETWEEN if both bounds given
            filter_expr = '{ modifier: BETWEEN, value: %d, value2: %d }' % (min_rating, max_rating)

        images: list[ScoredImage] = []
        page = 1
        while True:
            gql = """
            query {
                findImages(
                    filter: { page: %d, per_page: %d }
                    image_filter: { rating100: %s }
                ) {
                    count
                    images {
                        id
                        rating100
                        paths { thumbnail }
                    }
                }
            }
            """ % (page, page_size, filter_expr)
            data = self._query(gql)
            batch = data["findImages"]["images"]
            if not batch:
                break
            for img in batch:
                rating = img["rating100"] or 0
                images.append(ScoredImage(
                    stash_id=img["id"],
                    rating100=rating,
                    thumbnail_url=img["paths"]["thumbnail"],
                    label=rating / 100.0,
                ))
            log.info(f"  Fetched page {page} ({len(batch)} images, {len(images)} total)")
            if len(images) >= data["findImages"]["count"]:
                break
            page += 1
        return images

    def download_image(self, url: str, size: tuple[int, int] = (384, 384)) -> Optional[Image.Image]:
        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            img = img.resize(size, Image.LANCZOS)
            return img
        except Exception as e:
            log.debug(f"Failed to download {url}: {e}")
            return None


# ---------------------------------------------------------------------------
# SigLIP embedding extractor
# ---------------------------------------------------------------------------

class SigLIPEmbedder:
    """
    Wraps google/siglip-so400m-patch14-384 (same backbone used by the scorer
    service) to produce 1152-dim CLS embeddings.
    """
    def __init__(self, device: str = "auto"):
        from transformers import AutoProcessor, AutoModel
        log.info(f"Loading SigLIP model: {SIGLIP_MODEL_ID}")
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.processor = AutoProcessor.from_pretrained(SIGLIP_MODEL_ID)
        self.model = AutoModel.from_pretrained(
            SIGLIP_MODEL_ID,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        ).to(device)
        self.model.eval()
        log.info(f"SigLIP loaded on {device}")

    @torch.inference_mode()
    def embed(self, images: list[Image.Image], batch_size: int = 16) -> np.ndarray:
        all_embeddings = []
        for i in range(0, len(images), batch_size):
            batch = images[i : i + batch_size]
            inputs = self.processor(images=batch, return_tensors="pt",
                                    padding="max_length").to(self.device)
            outputs = self.model.vision_model(**{k: v for k, v in inputs.items()
                                                  if k in ("pixel_values",)})
            # CLS token → pooled representation
            pooled = outputs.pooler_output  # (B, 1152)
            all_embeddings.append(pooled.float().cpu().numpy())
        return np.concatenate(all_embeddings, axis=0)

    def embed_single(self, image: Image.Image) -> np.ndarray:
        return self.embed([image])[0]


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def build_dataset(
    stash: StashClient,
    embedder: SigLIPEmbedder,
    cache_path: Optional[Path] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns (embeddings, labels) arrays.
    If cache_path exists and is current, loads from it. Otherwise queries
    Stash, downloads thumbnails, computes embeddings, and saves the cache.
    """
    if cache_path and cache_path.exists():
        log.info(f"Loading embeddings from cache: {cache_path}")
        cached = np.load(cache_path, allow_pickle=True)
        return cached["embeddings"], cached["labels"]

    log.info("Fetching rated images from Stash...")
    high_images = stash.fetch_rated_images(min_rating=HIGH_RATING_MIN)
    low_images  = stash.fetch_rated_images(min_rating=1, max_rating=LOW_RATING_MAX)

    log.info(f"Found {len(high_images)} high-rated, {len(low_images)} low-rated images")

    all_images = high_images + low_images
    if len(all_images) == 0:
        raise ValueError("No rated images found in Stash. Rate some images first.")

    # Check class balance
    if len(high_images) < MIN_SAMPLES_PER_CLASS:
        log.warning(f"Only {len(high_images)} high-rated images (need {MIN_SAMPLES_PER_CLASS}+)")
    if len(low_images) < MIN_SAMPLES_PER_CLASS:
        log.warning(f"Only {len(low_images)} low-rated images (need {MIN_SAMPLES_PER_CLASS}+)")

    log.info("Downloading thumbnails and computing embeddings...")
    embeddings_list = []
    labels_list = []
    failed = 0

    for i, scored in enumerate(all_images):
        if i % 50 == 0:
            log.info(f"  Processing image {i+1}/{len(all_images)} (failed: {failed})")
        img = stash.download_image(scored.thumbnail_url)
        if img is None:
            failed += 1
            continue
        emb = embedder.embed_single(img)
        embeddings_list.append(emb)
        labels_list.append(scored.label)

    log.info(f"Embedding complete. {len(embeddings_list)} usable, {failed} failed downloads.")

    embeddings = np.stack(embeddings_list, axis=0)
    labels = np.array(labels_list, dtype=np.float32)

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache_path, embeddings=embeddings, labels=labels)
        log.info(f"Embeddings cached → {cache_path}")

    return embeddings, labels


def train(
    embeddings: np.ndarray,
    labels: np.ndarray,
    output_path: Path,
    epochs: int = DEFAULT_EPOCHS,
    batch_size: int = DEFAULT_BATCH,
    lr: float = DEFAULT_LR,
    val_split: float = 0.15,
    device: str = "auto",
) -> dict:
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    log.info(f"Training on {device} | samples={len(labels)} epochs={epochs} bs={batch_size} lr={lr}")

    dataset = EmbeddingDataset(embeddings, labels)
    n_val = max(1, int(len(dataset) * val_split))
    n_train = len(dataset) - n_val
    train_ds, val_ds = random_split(
        dataset, [n_train, n_val],
        generator=torch.Generator().manual_seed(42),
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=False)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False)

    model = CustomMLP(input_dim=embeddings.shape[1]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.BCELoss()

    best_val_loss = float("inf")
    best_state = None
    patience_counter = 0
    history = []

    for epoch in range(1, epochs + 1):
        # --- train ---
        model.train()
        train_loss = 0.0
        for X, y in train_loader:
            X, y = X.to(device), y.to(device)
            optimizer.zero_grad()
            pred = model(X)
            loss = criterion(pred, y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(y)
        train_loss /= n_train
        scheduler.step()

        # --- validate ---
        model.eval()
        val_loss = 0.0
        val_preds, val_targets = [], []
        with torch.no_grad():
            for X, y in val_loader:
                X, y = X.to(device), y.to(device)
                pred = model(X)
                val_loss += criterion(pred, y).item() * len(y)
                val_preds.extend(pred.cpu().numpy().tolist())
                val_targets.extend(y.cpu().numpy().tolist())
        val_loss /= n_val

        # Spearman correlation between predicted and actual ratings
        rho, _ = spearmanr(val_preds, val_targets) if len(val_preds) > 1 else (0.0, 1.0)

        history.append({"epoch": epoch, "train_loss": train_loss,
                         "val_loss": val_loss, "spearman_rho": float(rho)})

        if epoch % 5 == 0 or epoch == 1:
            log.info(f"  Epoch {epoch:>3}/{epochs} | "
                     f"train_loss={train_loss:.4f} val_loss={val_loss:.4f} ρ={rho:.3f}")

        # Early stopping
        if val_loss < best_val_loss - 1e-5:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= EARLY_STOP_PATIENCE:
                log.info(f"Early stopping at epoch {epoch} (no val improvement for {EARLY_STOP_PATIENCE} epochs)")
                break

    # Restore best weights
    if best_state:
        model.load_state_dict(best_state)

    metadata = {
        "n_train": n_train,
        "n_val": n_val,
        "best_val_loss": best_val_loss,
        "final_spearman_rho": history[-1]["spearman_rho"] if history else 0.0,
        "epochs_run": len(history),
        "high_rating_min": HIGH_RATING_MIN,
        "low_rating_max": LOW_RATING_MAX,
        "siglip_model": SIGLIP_MODEL_ID,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    model.save(output_path, metadata=metadata)
    return {"history": history, "metadata": metadata}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(weights_path: Path, embeddings: np.ndarray, labels: np.ndarray):
    model = CustomMLP.load(weights_path)
    model.eval()
    dataset = EmbeddingDataset(embeddings, labels)
    loader = DataLoader(dataset, batch_size=64, shuffle=False)

    all_preds, all_targets = [], []
    with torch.no_grad():
        for X, y in loader:
            pred = model(X)
            all_preds.extend(pred.numpy().tolist())
            all_targets.extend(y.numpy().tolist())

    preds = np.array(all_preds)
    targets = np.array(all_targets)
    rho, p = spearmanr(preds, targets)

    # Binary accuracy: high vs low (threshold at 0.5 label)
    binary_pred = (preds >= 0.5).astype(int)
    binary_true = (targets >= 0.5).astype(int)
    acc = (binary_pred == binary_true).mean()

    mse = ((preds - targets) ** 2).mean()

    log.info("=== Evaluation Results ===")
    log.info(f"  Samples:      {len(targets)}")
    log.info(f"  Spearman ρ:   {rho:.4f}  (p={p:.4f})")
    log.info(f"  Binary acc:   {acc:.4f}")
    log.info(f"  MSE:          {mse:.6f}")
    log.info(f"  Pred range:   [{preds.min():.3f}, {preds.max():.3f}]")
    log.info(f"  Label range:  [{targets.min():.3f}, {targets.max():.3f}]")

    return {"spearman_rho": float(rho), "binary_accuracy": float(acc), "mse": float(mse)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Train a custom MLP aesthetic scorer on Stash-rated images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true",
                      help="Count available training data in Stash and exit")
    mode.add_argument("--train", action="store_true",
                      help="Train the MLP (download embeddings + fit)")
    mode.add_argument("--evaluate", action="store_true",
                      help="Evaluate existing weights against rated images")
    mode.add_argument("--export-embeddings", action="store_true",
                      help="Only download thumbnails and compute/cache embeddings, no training")

    p.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS,
                   help=f"Path to save/load MLP weights (default: {DEFAULT_WEIGHTS})")
    p.add_argument("--embeddings-cache", type=Path, default=None,
                   help="Path to load/save embeddings cache (.npz). Skips re-downloading if present.")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                   help=f"Output directory for weights and logs (default: {DEFAULT_OUTPUT_DIR})")
    p.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    p.add_argument("--batch-size", type=int, default=DEFAULT_BATCH)
    p.add_argument("--lr", type=float, default=DEFAULT_LR)
    p.add_argument("--device", type=str, default="auto",
                   help="cuda / cpu / auto (default: auto)")
    p.add_argument("--high-min", type=int, default=HIGH_RATING_MIN,
                   help=f"Minimum rating100 to be 'positive' sample (default: {HIGH_RATING_MIN})")
    p.add_argument("--low-max", type=int, default=LOW_RATING_MAX,
                   help=f"Maximum rating100 to be 'negative' sample (default: {LOW_RATING_MAX})")
    p.add_argument("--stash-url", type=str, default=STASH_URL)
    p.add_argument("--stash-key", type=str, default=STASH_API_KEY,
                   help="Stash API key (or set STASH_API_KEY env var)")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Apply CLI overrides to module-level constants (used in StashClient)
    global HIGH_RATING_MIN, LOW_RATING_MAX
    HIGH_RATING_MIN = args.high_min
    LOW_RATING_MAX  = args.low_max

    stash = StashClient(url=args.stash_url, api_key=args.stash_key)

    # --check ----------------------------------------------------------------
    if args.check:
        log.info("Querying Stash for training data availability...")
        try:
            counts = stash.count_rated()
        except Exception as e:
            log.error(f"Failed to query Stash: {e}")
            sys.exit(1)
        print(f"\n=== Training Data Summary ===")
        print(f"  Total images in Stash: {counts['total']:,}")
        print(f"  High-rated (>={HIGH_RATING_MIN}/100): {counts['high']:,}")
        print(f"  Low-rated  (<={LOW_RATING_MAX}/100):  {counts['low']:,}")
        print(f"  Combined training pool: {counts['high'] + counts['low']:,}")
        if counts['high'] + counts['low'] < MIN_SAMPLES_PER_CLASS * 2:
            print(f"\n  WARNING: Not enough rated images for training.")
            print(f"  Rate at least {MIN_SAMPLES_PER_CLASS * 2} images in Stash first.")
        else:
            print(f"\n  Ready to train. Run with --train to start.")
        return

    # --export-embeddings ----------------------------------------------------
    if args.export_embeddings:
        cache = args.embeddings_cache or DEFAULT_CACHE
        embedder = SigLIPEmbedder(device=args.device)
        embeddings, labels = build_dataset(stash, embedder, cache_path=cache)
        log.info(f"Embeddings exported: shape={embeddings.shape}, cache={cache}")
        return

    # --train ----------------------------------------------------------------
    if args.train:
        embedder = SigLIPEmbedder(device=args.device)
        cache = args.embeddings_cache
        try:
            embeddings, labels = build_dataset(stash, embedder, cache_path=cache)
        except ValueError as e:
            log.error(str(e))
            sys.exit(1)

        if len(embeddings) < MIN_SAMPLES_PER_CLASS * 2:
            log.error(f"Only {len(embeddings)} samples. Need at least {MIN_SAMPLES_PER_CLASS * 2}. "
                      f"Rate more images in Stash then retry.")
            sys.exit(1)

        weights_path = args.weights
        if not weights_path.is_absolute():
            weights_path = args.output_dir / weights_path

        result = train(
            embeddings=embeddings,
            labels=labels,
            output_path=weights_path,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            device=args.device,
        )
        meta = result["metadata"]
        print(f"\n=== Training Complete ===")
        print(f"  Epochs run:       {meta['epochs_run']}")
        print(f"  Best val loss:    {meta['best_val_loss']:.4f}")
        print(f"  Spearman ρ:       {meta['final_spearman_rho']:.4f}")
        print(f"  Weights saved:    {weights_path}")

        # Save training history as JSON for later analysis
        history_path = weights_path.parent / "training_history.json"
        history_path.write_text(json.dumps(result["history"], indent=2))
        log.info(f"Training history → {history_path}")
        return

    # --evaluate -------------------------------------------------------------
    if args.evaluate:
        if not args.weights.exists():
            log.error(f"Weights not found: {args.weights}")
            sys.exit(1)
        embedder = SigLIPEmbedder(device=args.device)
        cache = args.embeddings_cache
        try:
            embeddings, labels = build_dataset(stash, embedder, cache_path=cache)
        except ValueError as e:
            log.error(str(e))
            sys.exit(1)
        evaluate(args.weights, embeddings, labels)
        return


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .db import conn_with_tenant, tx_with_tenant


@dataclass
class CachedKey:
    public_key_der: bytes
    fetched_at: float


class KMSPublicKeyCache:
    """In-process cache for signing public keys used for verification.

    Keyed by (kid, key_ref, alg). Falls back to DB ledger table `signing_public_keys`.
    """

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, str, str], CachedKey] = {}
        self.ttl_seconds = int(os.getenv("DADI_KMS_PUBKEY_CACHE_TTL_SECONDS", "3600"))

    def get(self, kid: str, key_ref: str, alg: str) -> Optional[bytes]:
        key = (kid, key_ref, alg)
        now = time.time()

        c = self._cache.get(key)
        if c and (now - c.fetched_at) <= self.ttl_seconds:
            return c.public_key_der

        try:
            with conn_with_tenant("default") as conn:
                row = conn.execute(
                    "SELECT public_key_der FROM signing_public_keys WHERE kid=%s AND key_ref=%s AND alg=%s AND active=TRUE",
                    (kid, key_ref, alg),
                ).fetchone()
            if row and row[0]:
                self._cache[key] = CachedKey(public_key_der=bytes(row[0]), fetched_at=now)
                return bytes(row[0])
        except Exception:
            return None

        return None

    def put(self, kid: str, key_ref: str, alg: str, public_key_der: bytes) -> None:
        key = (kid, key_ref, alg)
        now = time.time()
        self._cache[key] = CachedKey(public_key_der=public_key_der, fetched_at=now)

        try:
            with tx_with_tenant("default") as conn:
                conn.execute(
                    "INSERT INTO signing_public_keys (kid, key_ref, alg, public_key_der, first_seen_at, last_seen_at, active) "
                    "VALUES (%s,%s,%s,%s,now(),now(),TRUE) "
                    "ON CONFLICT (kid, key_ref, alg) DO UPDATE SET public_key_der=EXCLUDED.public_key_der, last_seen_at=now(), active=TRUE",
                    (kid, key_ref, alg, public_key_der),
                )
        except Exception:
            return


KMS_PUBKEY_CACHE = KMSPublicKeyCache()

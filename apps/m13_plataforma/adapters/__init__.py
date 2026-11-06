# Adaptadores de plataforma
from apps.m13_plataforma.adapters.email_sendgrid import SendGridEmailAdapter
from apps.m13_plataforma.adapters.storage_supabase import (
    PrivateBucketStorageAdapter,
    PublicBucketStorageAdapter,
    SupabaseStorageAdapter,
)

__all__ = [
    "SendGridEmailAdapter",
    "SupabaseStorageAdapter",
    "PublicBucketStorageAdapter",
    "PrivateBucketStorageAdapter",
]

from __future__ import annotations

import hashlib
from pathlib import Path

from cryptography.fernet import Fernet
from django.conf import settings


# 统一邮箱格式，避免大小写或首尾空白造成重复账户。
def normalize_email(email: str) -> str:
    return email.strip().lower()


# 生成邮箱哈希，用于数据库查重和查询。
def email_hash(email: str) -> str:
    return hashlib.sha256(normalize_email(email).encode("utf-8")).hexdigest()


# 使用本地 Fernet 密钥加密邮箱明文。
def encrypt_email(email: str) -> str:
    return _get_fernet().encrypt(normalize_email(email).encode("utf-8")).decode("ascii")


# 解密数据库中的邮箱密文，发送邮件时使用。
def decrypt_email(encrypted_email: str) -> str:
    return _get_fernet().decrypt(encrypted_email.encode("ascii")).decode("utf-8")


# 获取 Fernet 实例；密钥文件不存在时自动生成本地密钥。
def _get_fernet() -> Fernet:
    # 读取 settings 中配置的密钥文件路径。
    key_path = Path(settings.EMAIL_ENCRYPTION_KEY_PATH)

    # 确保密钥目录存在，便于首次启动自动生成密钥。
    key_path.parent.mkdir(parents=True, exist_ok=True)

    # 首次运行时生成密钥；真实部署必须保护该文件。
    if not key_path.exists():
        key_path.write_bytes(Fernet.generate_key())

    # 用文件中的密钥构造 Fernet 加解密器。
    key = key_path.read_bytes()
    return Fernet(key)

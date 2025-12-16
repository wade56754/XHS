"""
Cookie 加密模块

本模块提供 Cookie 的加密和解密功能，确保敏感信息安全存储。

安全设计:
1. 使用 AES-256 加密 (通过 Fernet)
2. 主密钥从环境变量加载，不在代码中硬编码
3. 支持密钥轮换 (通过 key_id 标识)
4. 使用 PBKDF2 进行密钥派生

使用方式:
    from media_crawler_api.utils.crypto import cookie_encryption

    # 加密
    encrypted, key_id = cookie_encryption.encrypt("cookie_value")

    # 解密
    plaintext = cookie_encryption.decrypt(encrypted, key_id)
"""

import os
import base64
from typing import Tuple, Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


class CookieEncryptionError(Exception):
    """Cookie 加密相关错误"""
    pass


class CookieEncryption:
    """
    Cookie 加密管理器

    提供 Cookie 的加密、解密功能，支持密钥轮换。

    环境变量配置:
    - COOKIE_MASTER_KEY: 主密钥 (必需，至少32字符)
    - COOKIE_KEY_SALT: 密钥派生盐值 (可选，默认 mediacrawler_v3)
    - COOKIE_KEY_ID: 当前密钥ID (可选，默认 key_v1)
    """

    # 密钥派生参数
    KDF_ITERATIONS = 100000
    KEY_LENGTH = 32  # 256 bits

    def __init__(self):
        self._keys: dict = {}
        self._current_key_id: Optional[str] = None
        self._initialized = False

    def initialize(self) -> None:
        """
        初始化加密器，加载密钥

        Raises:
            CookieEncryptionError: 如果主密钥未设置或无效
        """
        if self._initialized:
            return

        # 从环境变量加载主密钥
        master_key = os.environ.get("COOKIE_MASTER_KEY")
        if not master_key:
            raise CookieEncryptionError(
                "COOKIE_MASTER_KEY 环境变量未设置。"
                "请设置一个至少32字符的安全密钥。"
            )

        if len(master_key) < 32:
            raise CookieEncryptionError(
                f"COOKIE_MASTER_KEY 长度不足，当前 {len(master_key)} 字符，"
                "需要至少 32 字符。"
            )

        # 获取配置
        salt = os.environ.get("COOKIE_KEY_SALT", "mediacrawler_v3").encode()
        key_id = os.environ.get("COOKIE_KEY_ID", "key_v1")

        # 派生密钥
        derived_key = self._derive_key(master_key, salt)
        self._keys[key_id] = Fernet(derived_key)
        self._current_key_id = key_id
        self._initialized = True

    def _derive_key(self, master_key: str, salt: bytes) -> bytes:
        """
        从主密钥派生加密密钥

        Args:
            master_key: 主密钥字符串
            salt: 盐值

        Returns:
            派生的 Fernet 密钥 (base64 编码)
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=self.KDF_ITERATIONS,
            backend=default_backend()
        )
        key = kdf.derive(master_key.encode())
        return base64.urlsafe_b64encode(key)

    def encrypt(self, plaintext: str) -> Tuple[str, str]:
        """
        加密 Cookie 值

        Args:
            plaintext: 明文 Cookie 字符串

        Returns:
            (加密后的值, 使用的密钥ID)

        Raises:
            CookieEncryptionError: 加密失败
            ValueError: Cookie 值为空
        """
        if not self._initialized:
            self.initialize()

        if not plaintext:
            raise ValueError("Cookie 值不能为空")

        if not plaintext.strip():
            raise ValueError("Cookie 值不能为空白字符")

        try:
            fernet = self._keys[self._current_key_id]
            encrypted = fernet.encrypt(plaintext.encode('utf-8'))
            # 返回 base64 编码的密文
            encrypted_b64 = base64.urlsafe_b64encode(encrypted).decode('ascii')
            return encrypted_b64, self._current_key_id
        except Exception as e:
            raise CookieEncryptionError(f"加密失败: {e}")

    def decrypt(self, encrypted_value: str, key_id: str) -> str:
        """
        解密 Cookie 值

        Args:
            encrypted_value: 加密后的值 (base64 编码)
            key_id: 加密时使用的密钥 ID

        Returns:
            解密后的明文 Cookie

        Raises:
            CookieEncryptionError: 解密失败
        """
        if not self._initialized:
            self.initialize()

        if key_id not in self._keys:
            # 尝试加载历史密钥
            self._load_historical_key(key_id)

        try:
            fernet = self._keys[key_id]
            # 解码 base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode('ascii'))
            # 解密
            plaintext = fernet.decrypt(encrypted_bytes)
            return plaintext.decode('utf-8')
        except InvalidToken:
            raise CookieEncryptionError(
                f"解密失败: 无效的密文或密钥。key_id={key_id}"
            )
        except Exception as e:
            raise CookieEncryptionError(f"解密失败: {e}")

    def _load_historical_key(self, key_id: str) -> None:
        """
        加载历史密钥 (用于密钥轮换场景)

        Args:
            key_id: 历史密钥 ID

        Raises:
            CookieEncryptionError: 密钥未找到
        """
        # 环境变量格式: COOKIE_KEY_{KEY_ID} = master_key
        # 例如: COOKIE_KEY_KEY_V0 = old_master_key
        env_var = f"COOKIE_KEY_{key_id.upper().replace('-', '_')}"
        historical_master = os.environ.get(env_var)

        if not historical_master:
            raise CookieEncryptionError(
                f"历史密钥 {key_id} 未找到。"
                f"请设置环境变量 {env_var} 或重新加密数据。"
            )

        salt = os.environ.get("COOKIE_KEY_SALT", "mediacrawler_v3").encode()
        derived_key = self._derive_key(historical_master, salt)
        self._keys[key_id] = Fernet(derived_key)

    def rotate_key(self, encrypted_value: str, old_key_id: str) -> Tuple[str, str]:
        """
        轮换密钥: 用旧密钥解密，再用新密钥加密

        Args:
            encrypted_value: 用旧密钥加密的值
            old_key_id: 旧密钥 ID

        Returns:
            (新加密的值, 新密钥ID)
        """
        plaintext = self.decrypt(encrypted_value, old_key_id)
        return self.encrypt(plaintext)

    @property
    def current_key_id(self) -> str:
        """获取当前密钥 ID"""
        if not self._initialized:
            self.initialize()
        return self._current_key_id

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


# 创建单例实例
cookie_encryption = CookieEncryption()


# ============ 便捷函数 ============

def encrypt_cookie(cookie_value: str) -> Tuple[str, str]:
    """
    加密 Cookie (便捷函数)

    Args:
        cookie_value: Cookie 明文

    Returns:
        (加密值, 密钥ID)
    """
    return cookie_encryption.encrypt(cookie_value)


def decrypt_cookie(encrypted_value: str, key_id: str) -> str:
    """
    解密 Cookie (便捷函数)

    Args:
        encrypted_value: 加密值
        key_id: 密钥ID

    Returns:
        Cookie 明文
    """
    return cookie_encryption.decrypt(encrypted_value, key_id)


def mask_cookie(cookie_value: str, visible_chars: int = 8) -> str:
    """
    脱敏 Cookie 值用于日志显示

    Args:
        cookie_value: Cookie 值
        visible_chars: 显示的字符数

    Returns:
        脱敏后的字符串，如 "web_sess...xxx"
    """
    if not cookie_value:
        return "***EMPTY***"

    if len(cookie_value) <= visible_chars * 2:
        return "***REDACTED***"

    return f"{cookie_value[:visible_chars]}...{cookie_value[-4:]}"

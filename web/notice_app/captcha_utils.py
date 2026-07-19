from __future__ import annotations

import random
import string
from dataclasses import dataclass

from captcha.helpers import captcha_image_url
from captcha.models import CaptchaStore
from django.conf import settings
from django.utils import timezone


# 图形验证码响应数据，供 JSON API 返回给前端。
@dataclass(frozen=True, slots=True)
class CaptchaPayload:
    # django-simple-captcha 生成的验证码 hashkey。
    key: str

    # 图形验证码图片 URL。
    image_url: str


# 生成新的图形验证码，并返回前端展示所需的 key 和图片地址。
def create_captcha_payload() -> CaptchaPayload:
    # 清理过期验证码，避免验证码表长期膨胀。
    CaptchaStore.remove_expired()

    # 生成 CaptchaStore 记录，并通过库 helper 构造图片 URL。
    key = CaptchaStore.generate_key()
    return CaptchaPayload(key=key, image_url=captcha_image_url(key))


# 校验用户提交的图形验证码。
def validate_captcha_answer(key: str, answer: str) -> bool:
    # 缺失 key 或答案时直接判定失败。
    if not key or not answer:
        return False

    # 读取验证码记录，不存在时说明 key 已失效或被篡改。
    captcha = CaptchaStore.objects.filter(hashkey=key).first()
    if captcha is None:
        return False

    # 过期验证码不可继续使用。
    if captcha.expiration < timezone.now():
        captcha.delete()
        return False

    # 比对时统一忽略大小写和首尾空白。
    is_valid = captcha.response.lower() == answer.strip().lower()

    # 无论成功失败都作废当前验证码，降低重复尝试价值。
    captcha.delete()
    return is_valid


# 生成更混合的验证码字符，包含去掉易混淆字符后的大小写字母和数字。
def captcha_challenge() -> tuple[str, str]:
    # 避免 0/O、1/I/l 等容易误读字符，兼顾可读性和复杂度。
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    value = "".join(random.SystemRandom().choice(alphabet) for _ in range(settings.CAPTCHA_LENGTH))
    return value, value.lower()


# 为每个验证码字符生成不同但仍可读的深色。
def captcha_letter_color(index: int, challenge: str) -> str:
    # 使用暖色、绿色、蓝色之间的深色变化，增强干扰但不压低可读性。
    palette = ("#5f4735", "#7a4f2d", "#38644f", "#3f5f85", "#70475c")
    return palette[index % len(palette)]


# 添加额外干扰线，提升图形验证码复杂度。
def captcha_noise_lines(draw, image):
    # 获取图片尺寸，按尺寸随机绘制多条斜线和短线。
    width, height = image.size
    colors = ("#b08a6f", "#7a9b83", "#9b7a8d", "#c3a27e")

    # 随机生成干扰线，控制数量避免完全不可读。
    for _index in range(7):
        start = (random.randint(0, width), random.randint(0, height))
        end = (random.randint(0, width), random.randint(0, height))
        draw.line([start, end], fill=random.choice(colors), width=random.randint(1, 2))
    return draw

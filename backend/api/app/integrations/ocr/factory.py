from __future__ import annotations

from app.core.config import get_settings
from app.integrations.ocr.base import OCRProvider
from app.integrations.ocr.mock import MockOCRProvider

# Mapping `ocr_provider` (env config) -> factory function.
# Khi mở provider thật (PaddleOCR/EasyOCR/Vision API) ở phase tới,
# thêm entry vào dict này thay vì viết lại if-else.
_PROVIDER_REGISTRY: dict[str, type[OCRProvider]] = {
    "mock": MockOCRProvider,
}


def get_ocr_provider() -> OCRProvider:
    """Trả về implementation `OCRProvider` theo `settings.ocr_provider`.

    Fallback về `MockOCRProvider` nếu cấu hình không khớp registry để giữ
    pipeline OCR hoạt động được trong dev local kể cả khi env config sai.
    """
    settings = get_settings()
    provider_cls = _PROVIDER_REGISTRY.get(settings.ocr_provider, MockOCRProvider)
    return provider_cls()

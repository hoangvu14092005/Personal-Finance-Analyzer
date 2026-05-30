"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { DragEvent, FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import { FileText, RefreshCw, UploadCloud } from "lucide-react";

import { getMe } from "@/lib/auth-api";
import { getReceiptStatus, uploadReceipt } from "@/lib/receipts-api";
import {
  Button,
  CalloutBanner,
  Card,
  DisplayLg,
} from "@/components/ui";

type FlowState = "idle" | "uploading" | "processing" | "ready" | "failed";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_ATTEMPTS = 15;

const FLOW_STEPS = [
  { key: "upload", label: "Tải lên", detail: "Lưu ảnh/PDF hóa đơn" },
  { key: "ocr", label: "OCR Scan", detail: "Bóc tách ngày, cửa hàng, tổng tiền" },
  { key: "draft", label: "Kiểm tra", detail: "Sửa lại dữ liệu nhận diện" },
  { key: "confirm", label: "Ghi sổ", detail: "Đồng bộ vào giao dịch" },
];

function formatFileSize(file: File): string {
  if (file.size < 1024 * 1024) return `${Math.max(1, Math.round(file.size / 1024))} KB`;
  return `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ReceiptUploadPage() {
  const router = useRouter();

  const [authReady, setAuthReady] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [flowState, setFlowState] = useState<FlowState>("idle");
  const [message, setMessage] = useState("Chọn hóa đơn để upload.");
  const [receiptId, setReceiptId] = useState<number | null>(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await getMe();
        if (!cancelled) setAuthReady(true);
      } catch {
        if (!cancelled) router.replace("/login");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  const canSubmit = useMemo(
    () => selectedFile !== null && flowState !== "uploading" && flowState !== "processing",
    [selectedFile, flowState],
  );

  const pollUntilReady = async (id: number) => {
    for (let attempt = 1; attempt <= MAX_POLL_ATTEMPTS; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));

      try {
        const statusBody = await getReceiptStatus(id);
        if (statusBody.status === "ready") {
          setFlowState("ready");
          setMessage("OCR sẵn sàng. Đang chuyển sang trang review...");
          setTimeout(() => router.push(`/receipts/${id}/review`), 600);
          return;
        }
        if (statusBody.status === "failed") {
          setFlowState("failed");
          setMessage(
            statusBody.error_message || "OCR thất bại. Bạn có thể nhập tay.",
          );
          return;
        }
        setMessage(`Đang xử lý OCR... (lần ${attempt}/${MAX_POLL_ATTEMPTS})`);
      } catch (error) {
        setFlowState("failed");
        setMessage(
          error instanceof Error
            ? error.message
            : "Không lấy được trạng thái receipt.",
        );
        return;
      }
    }

    setFlowState("failed");
    setMessage("OCR chưa sẵn sàng sau nhiều lần kiểm tra. Bạn có thể nhập tay.");
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedFile) return;

    setFlowState("uploading");
    setMessage("Đang upload hóa đơn...");
    setReceiptId(null);

    try {
      const result = await uploadReceipt(selectedFile);
      setReceiptId(result.receipt_id);

      if (result.status === "ready") {
        setFlowState("ready");
        setMessage("OCR đã có sẵn. Đang chuyển sang trang review...");
        setTimeout(
          () => router.push(`/receipts/${result.receipt_id}/review`),
          400,
        );
        return;
      }

      if (result.status === "uploaded") {
        setFlowState("failed");
        setMessage(
          "OCR queue tạm không khả dụng. Bạn có thể nhập tay hoặc thử upload lại.",
        );
        return;
      }

      setFlowState("processing");
      setMessage(
        `Upload thành công. Đang chờ OCR (receipt #${result.receipt_id})...`,
      );
      await pollUntilReady(result.receipt_id);
    } catch (error) {
      setFlowState("failed");
      setMessage(error instanceof Error ? error.message : "Upload thất bại");
    }
  };

  const onDropFile = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragActive(false);
    const file = event.dataTransfer.files?.[0];
    if (file) setSelectedFile(file);
  };

  if (!authReady) {
    return (
      <Card>
        <p className="text-body-sm text-mute">Đang xác thực phiên đăng nhập...</p>
      </Card>
    );
  }

  const severity: "info" | "success" | "warning" =
    flowState === "ready"
      ? "success"
      : flowState === "failed"
        ? "warning"
        : "info";

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <DisplayLg>Tự Động Trích Xuất Hóa Đơn (OCR Scan)</DisplayLg>
            <p className="mt-0.5 text-sm text-ash">
              Tải ảnh hóa đơn lên để AI bóc tách chi tiết từng sản phẩm, ngày mua và tự động ghi sổ tài chính nhanh chóng.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/receipts">
              <Button type="button" variant="secondary" size="sm">Nhật ký hóa đơn</Button>
            </Link>
            <Link href="/transactions/new">
              <Button type="button" variant="secondary" size="sm">Ghi chép thủ công</Button>
            </Link>
          </div>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-4">
          {FLOW_STEPS.map((step, index) => (
            <div key={step.key} className="rounded-xl border border-hairline-soft bg-white p-4">
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-green-soft text-caption-xs font-black text-accent-green">
                  {index + 1}
                </span>
                <div>
                  <p className="text-body-strong text-ink">{step.label}</p>
                  <p className="text-caption-sm text-mute">{step.detail}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-12">
        <Card className="border-hairline-soft bg-white xl:col-span-8">
          <form className="space-y-5" onSubmit={onSubmit}>
            <label
              onDragEnter={(event) => {
                event.preventDefault();
                setDragActive(true);
              }}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={() => setDragActive(false)}
              onDrop={onDropFile}
              className={`block cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition-colors ${
                dragActive
                  ? "border-accent-green bg-accent-green-soft"
                  : "border-hairline-soft bg-surface-doc hover:border-accent-green/60 hover:bg-surface-soft"
              }`}
            >
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                className="sr-only"
              />
              <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-accent-green-soft text-body-strong text-accent-green">
                {flowState === "processing" || flowState === "uploading" ? (
                  <RefreshCw className="h-6 w-6 animate-spin" aria-hidden />
                ) : selectedFile ? (
                  <FileText className="h-6 w-6" aria-hidden />
                ) : (
                  <UploadCloud className="h-6 w-6" aria-hidden />
                )}
              </span>
              <span className="mt-4 block text-heading-sm-mixed text-ink">
                Kéo thả hóa đơn vào đây hoặc click để chọn file
              </span>
              <span className="mt-2 block text-body-sm text-mute">
                Hỗ trợ JPG, PNG, PDF. AI sẽ bóc tách hóa đơn và chuyển sang màn kiểm tra.
              </span>
              {selectedFile ? (
                <span className="mx-auto mt-4 flex max-w-xl items-center justify-between gap-3 rounded-xl border border-hairline-soft bg-surface-card px-4 py-3 text-left">
                  <span className="min-w-0">
                    <span className="block truncate text-body-strong text-ink">{selectedFile.name}</span>
                    <span className="block text-caption-sm text-mute">{formatFileSize(selectedFile)} · sẵn sàng tải lên</span>
                  </span>
                  <span className="rounded-md bg-accent-green-soft px-2 py-1 text-caption-xs text-accent-green">Đã chọn</span>
                </span>
              ) : null}
            </label>

            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" variant="primary" disabled={!canSubmit}>
                {flowState === "uploading"
                  ? "Đang upload..."
                  : flowState === "processing"
                    ? "Đang xử lý OCR..."
                    : "Tải lên và quét OCR"}
              </Button>
              {receiptId && flowState === "ready" ? (
                <Link href={`/receipts/${receiptId}/review`}>
                  <Button type="button" variant="secondary">Mở màn kiểm tra</Button>
                </Link>
              ) : null}
            </div>
          </form>
        </Card>

        <aside className="space-y-4 xl:col-span-4">
          <CalloutBanner severity={severity} title={`Trạng thái: ${flowState.toUpperCase()}`}>
            {message}
            {receiptId ? ` (Receipt ID: ${receiptId})` : null}
          </CalloutBanner>

          <Card className="border-hairline-soft bg-surface-card">
            <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">Cơ chế ghi sổ</p>
            <h2 className="mt-1 text-heading-sm-mixed text-ink">Kiểm tra trước khi đồng bộ</h2>
            <p className="mt-2 text-body-sm text-body">
              Hóa đơn sau khi OCR sẽ mở màn kiểm tra. Bạn xác nhận xong thì hệ thống mới ghi vào sổ giao dịch.
            </p>
          </Card>

          {flowState === "failed" ? (
            <Card className="border-accent-red/30 bg-accent-red-soft">
              <p className="mb-2 text-body-strong text-ink">Không sẵn sàng review từ OCR</p>
              <p className="text-body-sm text-body">
                Bạn có thể{" "}
                <Link href="/transactions/new" className="font-semibold text-link-teal hover:underline">
                  nhập giao dịch thủ công
                </Link>{" "}
                hoặc thử upload lại.
              </p>
            </Card>
          ) : null}
        </aside>
      </div>
    </div>
  );
}

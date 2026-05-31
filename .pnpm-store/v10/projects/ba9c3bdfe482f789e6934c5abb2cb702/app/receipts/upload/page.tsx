"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { DragEvent, FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, FileText, RefreshCw, UploadCloud, XCircle } from "lucide-react";

import { getMe } from "@/lib/auth-api";
import { getReceiptStatus, uploadReceipt } from "@/lib/receipts-api";
import {
  Button,
  CalloutBanner,
  Card,
  DisplayLg,
} from "@/components/ui";

// OCR llm_vision gọi LLM nhiều lần nên có thể chậm. Cho phép chờ tới ~3 phút.
const POLL_INTERVAL_MS = 2500;
const MAX_POLL_ATTEMPTS = 72;
const MAX_FILES = 10;

type ItemState =
  | "queued"
  | "uploading"
  | "processing"
  | "ready"
  | "failed"
  | "slow";

interface UploadItem {
  id: string; // local key
  file: File;
  state: ItemState;
  receiptId: number | null;
  message: string;
}

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

function makeKey(file: File, index: number): string {
  return `${file.name}-${file.size}-${file.lastModified}-${index}-${Date.now()}`;
}

export default function ReceiptUploadPage() {
  const router = useRouter();

  const [authReady, setAuthReady] = useState(false);
  const [items, setItems] = useState<UploadItem[]>([]);
  const [running, setRunning] = useState(false);
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

  const summary = useMemo(() => {
    return {
      total: items.length,
      ready: items.filter((i) => i.state === "ready").length,
      failed: items.filter((i) => i.state === "failed").length,
      slow: items.filter((i) => i.state === "slow").length,
    };
  }, [items]);

  const allDone =
    items.length > 0 &&
    items.every((i) => ["ready", "failed", "slow"].includes(i.state));

  const addFiles = (files: FileList | File[]) => {
    const incoming = Array.from(files);
    setItems((prev) => {
      const room = Math.max(0, MAX_FILES - prev.length);
      const slice = incoming.slice(0, room);
      const next = slice.map((file, idx) => ({
        id: makeKey(file, prev.length + idx),
        file,
        state: "queued" as ItemState,
        receiptId: null,
        message: "Chờ tải lên",
      }));
      return [...prev, ...next];
    });
  };

  const patchItem = (id: string, patch: Partial<UploadItem>) => {
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, ...patch } : i)));
  };

  const removeItem = (id: string) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
  };

  const pollUntilReady = async (id: string, receiptId: number) => {
    for (let attempt = 1; attempt <= MAX_POLL_ATTEMPTS; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      try {
        const statusBody = await getReceiptStatus(receiptId);
        if (statusBody.status === "ready") {
          patchItem(id, { state: "ready", message: "OCR xong, sẵn sàng kiểm tra" });
          return;
        }
        if (statusBody.status === "failed") {
          patchItem(id, {
            state: "failed",
            message: statusBody.error_message || "OCR thất bại. Có thể nhập tay.",
          });
          return;
        }
        patchItem(id, { state: "processing", message: "Đang xử lý hóa đơn..." });
      } catch (error) {
        patchItem(id, {
          state: "failed",
          message:
            error instanceof Error ? error.message : "Không lấy được trạng thái.",
        });
        return;
      }
    }
    // Vẫn đang xử lý (không phải lỗi) — worker llm_vision có thể chậm.
    patchItem(id, {
      state: "slow",
      message: "OCR đang xử lý lâu hơn dự kiến, hóa đơn vẫn đang chạy.",
    });
  };

  const processOne = async (item: UploadItem) => {
    patchItem(item.id, { state: "uploading", message: "Đang tải lên..." });
    try {
      const result = await uploadReceipt(item.file);
      if (result.status === "ready") {
        patchItem(item.id, {
          state: "ready",
          receiptId: result.receipt_id,
          message: "OCR xong, sẵn sàng kiểm tra",
        });
        return;
      }
      if (result.status === "uploaded") {
        patchItem(item.id, {
          state: "failed",
          receiptId: result.receipt_id,
          message: "OCR queue tạm không khả dụng. Thử lại sau.",
        });
        return;
      }
      patchItem(item.id, {
        state: "processing",
        receiptId: result.receipt_id,
        message: "Đang xử lý hóa đơn...",
      });
      await pollUntilReady(item.id, result.receipt_id);
    } catch (error) {
      patchItem(item.id, {
        state: "failed",
        message: error instanceof Error ? error.message : "Upload thất bại",
      });
    }
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const queued = items.filter((i) => i.state === "queued");
    if (queued.length === 0) return;

    setRunning(true);
    // Upload tuần tự từng file (worker xử lý OCR song song ở backend).
    for (const item of queued) {
      // Lấy bản mới nhất của item (state có thể đã đổi).
      await processOne(item);
    }
    setRunning(false);

    // Nếu chỉ có 1 file và xong (ready) → nhảy thẳng tới review cho nhanh.
    setItems((current) => {
      const readyOnes = current.filter((i) => i.state === "ready" && i.receiptId);
      if (current.length === 1 && readyOnes.length === 1 && readyOnes[0].receiptId) {
        router.push(`/receipts/${readyOnes[0].receiptId}/review`);
      }
      return current;
    });
  };

  const recheck = async (item: UploadItem) => {
    if (item.receiptId === null) return;
    patchItem(item.id, { state: "processing", message: "Đang kiểm tra lại..." });
    await pollUntilReady(item.id, item.receiptId);
  };

  const onDropFiles = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragActive(false);
    if (event.dataTransfer.files?.length) addFiles(event.dataTransfer.files);
  };

  if (!authReady) {
    return (
      <Card>
        <p className="text-body-sm text-mute">Đang xác thực phiên đăng nhập...</p>
      </Card>
    );
  }

  const queuedCount = items.filter((i) => i.state === "queued").length;

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <DisplayLg>Tự Động Trích Xuất Hóa Đơn (OCR Scan)</DisplayLg>
            <p className="mt-0.5 text-sm text-ash">
              Tải một hoặc nhiều hóa đơn lên để AI bóc tách chi tiết và tự động ghi sổ tài chính.
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
              onDrop={onDropFiles}
              className={`block cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition-colors ${
                dragActive
                  ? "border-accent-green bg-accent-green-soft"
                  : "border-hairline-soft bg-surface-doc hover:border-accent-green/60 hover:bg-surface-soft"
              }`}
            >
              <input
                type="file"
                multiple
                accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
                onChange={(event) => {
                  if (event.target.files?.length) addFiles(event.target.files);
                  event.target.value = "";
                }}
                className="sr-only"
              />
              <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-accent-green-soft text-body-strong text-accent-green">
                {running ? (
                  <RefreshCw className="h-6 w-6 animate-spin" aria-hidden />
                ) : (
                  <UploadCloud className="h-6 w-6" aria-hidden />
                )}
              </span>
              <span className="mt-4 block text-heading-sm-mixed text-ink">
                Kéo thả nhiều hóa đơn vào đây hoặc click để chọn file
              </span>
              <span className="mt-2 block text-body-sm text-mute">
                Hỗ trợ JPG, PNG, PDF. Tối đa {MAX_FILES} hóa đơn mỗi lần.
              </span>
            </label>

            {items.length > 0 ? (
              <ul className="space-y-2">
                {items.map((item) => (
                  <UploadRow
                    key={item.id}
                    item={item}
                    onRemove={() => removeItem(item.id)}
                    onRecheck={() => void recheck(item)}
                    disabled={running}
                  />
                ))}
              </ul>
            ) : null}

            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" variant="primary" disabled={running || queuedCount === 0}>
                {running
                  ? "Đang xử lý..."
                  : queuedCount > 0
                    ? `Tải lên và quét OCR (${queuedCount})`
                    : "Tải lên và quét OCR"}
              </Button>
              {allDone && summary.ready > 0 ? (
                <Link href="/receipts">
                  <Button type="button" variant="secondary">Xem danh sách hóa đơn</Button>
                </Link>
              ) : null}
            </div>
          </form>
        </Card>

        <aside className="space-y-4 xl:col-span-4">
          <CalloutBanner
            severity={summary.failed > 0 ? "warning" : allDone ? "success" : "info"}
            title={`Hóa đơn: ${summary.total} · Xong: ${summary.ready}`}
          >
            {items.length === 0
              ? "Chọn một hoặc nhiều hóa đơn để bắt đầu."
              : running
                ? "Đang xử lý hóa đơn..."
                : allDone
                  ? `Hoàn tất: ${summary.ready} sẵn sàng, ${summary.failed} lỗi, ${summary.slow} đang chạy.`
                  : "Sẵn sàng tải lên."}
          </CalloutBanner>

          <Card className="border-hairline-soft bg-surface-card">
            <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">Cơ chế ghi sổ</p>
            <h2 className="mt-1 text-heading-sm-mixed text-ink">Kiểm tra trước khi đồng bộ</h2>
            <p className="mt-2 text-body-sm text-body">
              Mỗi hóa đơn sau khi OCR xong sẽ chờ ở danh sách để bạn kiểm tra rồi mới ghi vào sổ giao dịch.
            </p>
          </Card>
        </aside>
      </div>
    </div>
  );
}

function stateMeta(state: ItemState): { label: string; tone: string } {
  switch (state) {
    case "ready":
      return { label: "Sẵn sàng", tone: "text-accent-green" };
    case "failed":
      return { label: "Lỗi", tone: "text-accent-red" };
    case "slow":
      return { label: "Đang chạy", tone: "text-primary-active" };
    case "uploading":
      return { label: "Đang tải lên", tone: "text-link-blue" };
    case "processing":
      return { label: "Đang xử lý", tone: "text-link-blue" };
    default:
      return { label: "Chờ", tone: "text-mute" };
  }
}

function UploadRow({
  item,
  onRemove,
  onRecheck,
  disabled,
}: {
  item: UploadItem;
  onRemove: () => void;
  onRecheck: () => void;
  disabled: boolean;
}) {
  const meta = stateMeta(item.state);
  const busy = item.state === "uploading" || item.state === "processing";
  return (
    <li className="flex items-center gap-3 rounded-xl border border-hairline-soft bg-surface-doc px-4 py-3">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white text-mute">
        {item.state === "ready" ? (
          <CheckCircle2 className="h-5 w-5 text-accent-green" aria-hidden />
        ) : item.state === "failed" ? (
          <XCircle className="h-5 w-5 text-accent-red" aria-hidden />
        ) : busy ? (
          <RefreshCw className="h-5 w-5 animate-spin" aria-hidden />
        ) : (
          <FileText className="h-5 w-5" aria-hidden />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-body-sm font-semibold text-ink">{item.file.name}</p>
        <p className="truncate text-caption-sm text-mute">
          {formatFileSize(item.file)} · <span className={meta.tone}>{meta.label}</span>
          {item.message ? ` · ${item.message}` : ""}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {item.state === "ready" && item.receiptId ? (
          <Link href={`/receipts/${item.receiptId}/review`}>
            <Button type="button" variant="secondary" size="sm">Kiểm tra</Button>
          </Link>
        ) : null}
        {item.state === "slow" && item.receiptId ? (
          <Button type="button" variant="secondary" size="sm" onClick={onRecheck}>
            Kiểm tra lại
          </Button>
        ) : null}
        {item.state === "queued" && !disabled ? (
          <Button type="button" variant="tertiary" size="sm" onClick={onRemove}>
            Bỏ
          </Button>
        ) : null}
      </div>
    </li>
  );
}

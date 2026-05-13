"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

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

export default function ReceiptUploadPage() {
  const router = useRouter();

  const [authReady, setAuthReady] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [flowState, setFlowState] = useState<FlowState>("idle");
  const [message, setMessage] = useState("Chọn hóa đơn để upload.");
  const [receiptId, setReceiptId] = useState<number | null>(null);

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
    <div className="max-w-2xl mx-auto space-y-6">
      <header>
        <DisplayLg>Upload hóa đơn</DisplayLg>
        <p className="text-body-sm text-body mt-1">
          Hỗ trợ JPG, PNG, PDF 1 trang. AI tự đọc thông tin và tạo draft.
        </p>
      </header>

      <Card>
        <form className="space-y-4" onSubmit={onSubmit}>
          <label className="block">
            <span className="text-body-xs text-ink">Chọn file</span>
            <div className="mt-2 rounded-md border border-dashed border-hairline bg-surface-doc p-6 text-center">
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                className="block w-full text-body-sm text-body"
              />
              {selectedFile && (
                <p className="mt-2 text-caption-sm text-mute">
                  Đã chọn: <span className="text-ink font-medium">{selectedFile.name}</span>
                </p>
              )}
            </div>
          </label>

          <Button type="submit" variant="primary" disabled={!canSubmit}>
            {flowState === "uploading"
              ? "Đang upload..."
              : flowState === "processing"
                ? "Đang xử lý OCR..."
                : "Upload hóa đơn"}
          </Button>
        </form>
      </Card>

      <CalloutBanner severity={severity} title={`Trạng thái: ${flowState.toUpperCase()}`}>
        {message}
        {receiptId ? ` (Receipt ID: ${receiptId})` : null}
      </CalloutBanner>

      {flowState === "failed" ? (
        <Card>
          <p className="text-body-strong text-ink mb-2">
            Không sẵn sàng review từ OCR
          </p>
          <p className="text-body-sm text-body">
            Bạn có thể{" "}
            <Link
              href="/transactions/new"
              className="text-link-teal font-semibold hover:underline"
            >
              nhập giao dịch thủ công
            </Link>{" "}
            hoặc thử upload lại.
          </p>
        </Card>
      ) : null}
    </div>
  );
}

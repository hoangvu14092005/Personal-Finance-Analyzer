"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { getMe } from "@/lib/auth-api";
import { getReceiptStatus, uploadReceipt } from "@/lib/receipts-api";

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
        // Queue unavailable: backend đặt status="uploaded" + error_code; user
        // có thể chuyển sang nhập tay hoặc thử lại sau.
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
      <section className="rounded-2xl border border-slate-200 bg-white p-8">
        <p className="text-sm text-slate-600">Đang xác thực phiên đăng nhập...</p>
      </section>
    );
  }

  return (
    <section className="space-y-6 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Upload hóa đơn</h1>
        <p className="text-sm text-slate-600">
          Hỗ trợ JPG, PNG, PDF 1 trang. Sau khi OCR xong sẽ chuyển sang trang review.
        </p>
      </header>

      <form className="space-y-4" onSubmit={onSubmit}>
        <input
          type="file"
          accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
          onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          className="block w-full text-sm text-slate-700"
        />
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {flowState === "uploading"
            ? "Đang upload..."
            : flowState === "processing"
              ? "Đang xử lý OCR..."
              : "Upload hóa đơn"}
        </button>
      </form>

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
        <p className="font-semibold">Trạng thái: {flowState.toUpperCase()}</p>
        <p className="mt-1">{message}</p>
        {receiptId ? <p className="mt-1">Receipt ID: {receiptId}</p> : null}
      </div>

      {flowState === "failed" ? (
        <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">Không sẵn sàng review từ OCR</p>
          <p>
            Bạn có thể{" "}
            <Link href="/transactions/new" className="font-semibold underline">
              nhập giao dịch thủ công
            </Link>{" "}
            hoặc thử upload lại.
          </p>
        </div>
      ) : null}
    </section>
  );
}

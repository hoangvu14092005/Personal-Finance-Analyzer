"use client";

import { FormEvent, useMemo, useState } from "react";

import { apiBaseUrl } from "@/lib/config";

type FlowState = "idle" | "uploading" | "processing" | "ready" | "failed";

type ReceiptStatus = {
  receipt_id: number;
  status: string;
  error_message: string | null;
};

type OcrResult = {
  provider: string;
  normalized_payload: string | null;
  raw_text: string | null;
};

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_ATTEMPTS = 10;

export default function ReceiptUploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [flowState, setFlowState] = useState<FlowState>("idle");
  const [message, setMessage] = useState("Chon hoa don de upload.");
  const [receiptId, setReceiptId] = useState<number | null>(null);
  const [ocrResult, setOcrResult] = useState<OcrResult | null>(null);

  const canSubmit = useMemo(() => selectedFile !== null && flowState !== "uploading", [selectedFile, flowState]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedFile) {
      return;
    }

    setFlowState("uploading");
    setMessage("Dang upload hoa don...");
    setOcrResult(null);

    try {
      const form = new FormData();
      form.append("file", selectedFile);

      const uploadResponse = await fetch(`${apiBaseUrl}/api/v1/receipts/upload`, {
        method: "POST",
        body: form,
        credentials: "include",
      });

      if (!uploadResponse.ok) {
        const body = (await uploadResponse.json()) as { detail?: string };
        throw new Error(body.detail || "Upload that bai");
      }

      const uploadBody = (await uploadResponse.json()) as { receipt_id: number; status: string };
      setReceiptId(uploadBody.receipt_id);
      setFlowState("processing");
      setMessage(`Upload thanh cong. Dang cho OCR (receipt #${uploadBody.receipt_id})...`);

      await pollReceipt(uploadBody.receipt_id);
    } catch (error) {
      setFlowState("failed");
      setMessage(error instanceof Error ? error.message : "Upload that bai");
    }
  };

  const pollReceipt = async (id: number) => {
    for (let attempt = 1; attempt <= MAX_POLL_ATTEMPTS; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));

      const statusResponse = await fetch(`${apiBaseUrl}/api/v1/receipts/${id}`, {
        method: "GET",
        credentials: "include",
      });

      if (!statusResponse.ok) {
        setFlowState("failed");
        setMessage("Khong lay duoc trang thai receipt.");
        return;
      }

      const statusBody = (await statusResponse.json()) as ReceiptStatus;
      if (statusBody.status === "ready") {
        const resultResponse = await fetch(`${apiBaseUrl}/api/v1/receipts/${id}/ocr-result`, {
          method: "GET",
          credentials: "include",
        });

        if (resultResponse.ok) {
          const resultBody = (await resultResponse.json()) as OcrResult;
          setOcrResult(resultBody);
        }

        setFlowState("ready");
        setMessage("OCR da san sang. Ban co the review draft.");
        return;
      }

      if (statusBody.status === "failed") {
        setFlowState("failed");
        setMessage(statusBody.error_message || "OCR that bai. Vui long nhap tay.");
        return;
      }

      setMessage(`Dang xu ly OCR... (lan ${attempt}/${MAX_POLL_ATTEMPTS})`);
    }

    setFlowState("failed");
    setMessage("OCR chua san sang. Ban co the chuyen sang nhap tay.");
  };

  return (
    <section className="space-y-6 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <h1 className="text-2xl font-bold text-slate-900">Receipt Upload</h1>
      <p className="text-sm text-slate-600">Ho tro JPG, PNG, PDF 1 trang. Upload va cho OCR xu ly.</p>

      <form className="space-y-4" onSubmit={onSubmit}>
        <input
          type="file"
          accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
          onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
        />
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {flowState === "uploading" ? "Dang upload..." : "Upload hoa don"}
        </button>
      </form>

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
        <p className="font-semibold">Trang thai: {flowState.toUpperCase()}</p>
        <p className="mt-1">{message}</p>
        {receiptId ? <p className="mt-1">Receipt ID: {receiptId}</p> : null}
      </div>

      {flowState === "ready" && ocrResult ? (
        <div className="space-y-2 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          <p className="font-semibold">OCR Ready ({ocrResult.provider})</p>
          <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-white p-3 text-xs text-slate-700">
            {ocrResult.normalized_payload || ocrResult.raw_text || "No OCR payload"}
          </pre>
        </div>
      ) : null}

      {flowState === "failed" ? (
        <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">Fallback Manual Entry</p>
          <p>
            OCR khong san sang. Ban co the nhap thu cong thong tin giao dich o phase 3.
          </p>
        </div>
      ) : null}
    </section>
  );
}

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { QRCodeSVG } from "qrcode.react";
import { setupTotp, confirmTotp } from "../../api/users";
import { useAuthStore } from "../../store/auth";

export default function PortalProfile() {
  const { userId } = useAuthStore();
  const [totpSetup, setTotpSetup] = useState<{ secret: string; uri: string } | null>(null);
  const [totpCode, setTotpCode] = useState("");

  const setupMutation = useMutation({
    mutationFn: setupTotp,
    onSuccess: (data) => setTotpSetup(data),
    onError: () => toast.error("Failed to start TOTP setup"),
  });

  const confirmMutation = useMutation({
    mutationFn: () => confirmTotp(totpSetup!.secret, totpCode),
    onSuccess: () => { toast.success("TOTP enabled!"); setTotpSetup(null); setTotpCode(""); },
    onError: () => toast.error("Invalid code — try again"),
  });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Profile</h1>

      <div className="bg-white rounded-xl shadow-sm p-6 max-w-md">
        <h2 className="text-lg font-semibold mb-4">Two-Factor Authentication</h2>

        {!totpSetup ? (
          <button
            onClick={() => setupMutation.mutate()}
            disabled={setupMutation.isPending}
            className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {setupMutation.isPending ? "Setting up…" : "Set up TOTP"}
          </button>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">Scan this QR code with your authenticator app:</p>
            <div className="flex justify-center">
              <QRCodeSVG value={totpSetup.uri} size={200} />
            </div>
            <p className="text-xs text-gray-400 font-mono break-all">Secret: {totpSetup.secret}</p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Confirm code</label>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                placeholder="123456"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => confirmMutation.mutate()}
                disabled={totpCode.length !== 6 || confirmMutation.isPending}
                className="bg-brand-600 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
              >
                Confirm
              </button>
              <button onClick={() => setTotpSetup(null)} className="text-gray-500 text-sm px-3">Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

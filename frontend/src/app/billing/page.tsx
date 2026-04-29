"use client";

import { useEffect, useState } from "react";
import NavBar from "@/components/NavBar";
import { useRequireAuth } from "@/lib/auth";
import { payments as paymentsApi, SubscriptionStatus } from "@/lib/api";

export default function BillingPage() {
  const { authenticated } = useRequireAuth();
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (!authenticated) return;
    paymentsApi.subscription().then((s) => {
      setStatus(s);
      setLoading(false);
    }).catch((err) => {
      setError(err instanceof Error ? err.message : "Failed to load subscription");
      setLoading(false);
    });
  }, [authenticated]);

  async function handleCheckout() {
    setActionLoading(true);
    try {
      const { url } = await paymentsApi.createCheckoutSession();
      window.location.href = url;
    } catch (err) {
      alert(err instanceof Error ? err.message : "Could not start checkout");
    } finally {
      setActionLoading(false);
    }
  }

  async function handlePortal() {
    setActionLoading(true);
    try {
      const { url } = await paymentsApi.openPortal();
      window.location.href = url;
    } catch (err) {
      alert(err instanceof Error ? err.message : "Could not open billing portal");
    } finally {
      setActionLoading(false);
    }
  }

  if (!authenticated) return null;

  return (
    <>
      <NavBar />
      <main className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Billing &amp; Subscription</h1>

        {loading && <p className="text-gray-500 text-sm">Loading subscription…</p>}
        {error && <p className="text-red-500 text-sm">{error}</p>}

        {!loading && !error && status && (
          <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-3">
              <span
                className={`text-sm px-3 py-1 rounded-full font-medium ${
                  status.status === "active"
                    ? "bg-green-100 text-green-700"
                    : "bg-gray-100 text-gray-600"
                }`}
              >
                {status.status}
              </span>
              {status.plan && (
                <span className="text-sm font-semibold text-gray-800">
                  {status.plan} plan
                </span>
              )}
            </div>

            {status.current_period_end && (
              <p className="text-sm text-gray-500">
                Current period ends:{" "}
                <span className="text-gray-800 font-medium">
                  {new Date(status.current_period_end).toLocaleDateString()}
                </span>
              </p>
            )}

            <div className="flex gap-3 pt-2">
              {status.status !== "active" && (
                <button
                  onClick={handleCheckout}
                  disabled={actionLoading}
                  className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-60"
                >
                  {actionLoading ? "Loading…" : "Upgrade to Pro"}
                </button>
              )}
              {status.status === "active" && (
                <button
                  onClick={handlePortal}
                  disabled={actionLoading}
                  className="bg-white border border-gray-300 text-gray-700 px-5 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors disabled:opacity-60"
                >
                  {actionLoading ? "Loading…" : "Manage Subscription"}
                </button>
              )}
            </div>
          </div>
        )}

        {!loading && !error && !status && (
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <p className="text-gray-600 mb-4">You don&apos;t have an active subscription.</p>
            <button
              onClick={handleCheckout}
              disabled={actionLoading}
              className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-60"
            >
              {actionLoading ? "Loading…" : "Upgrade to Pro"}
            </button>
          </div>
        )}
      </main>
    </>
  );
}

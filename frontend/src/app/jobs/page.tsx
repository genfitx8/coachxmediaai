"use client";

import { useEffect, useState, FormEvent, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import NavBar from "@/components/NavBar";
import { useRequireAuth } from "@/lib/auth";
import { jobs as jobsApi, JobRead, projects as projectsApi, ProjectRead } from "@/lib/api";

const JOB_TYPES = [
  "transcription",
  "summarization",
  "comparison",
  "highlight_extraction",
];

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

function JobsContent() {
  const { authenticated } = useRequireAuth();
  const searchParams = useSearchParams();
  const preselectedProject = searchParams.get("project") ?? "";

  const [items, setItems] = useState<JobRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [projectsList, setProjectsList] = useState<ProjectRead[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [jobType, setJobType] = useState(JOB_TYPES[0]);
  const [projectId, setProjectId] = useState(preselectedProject);
  const [mediaId, setMediaId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Polling interval ref
  const [pollingIds, setPollingIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!authenticated) return;

    let cancelled = false;

    async function fetchInitialData() {
      setError(null);
      try {
        const [jobsData, projectsData] = await Promise.all([
          jobsApi.list(),
          projectsApi.list(),
        ]);
        if (!cancelled) {
          setItems(jobsData);
          setProjectsList(projectsData);
          setPollingIds(
            new Set(
              jobsData
                .filter((j) => ["pending", "running"].includes(j.status))
                .map((j) => j.id)
            )
          );
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load jobs");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchInitialData();

    return () => {
      cancelled = true;
    };
  }, [authenticated]);

  // Poll active jobs every 5s
  useEffect(() => {
    if (pollingIds.size === 0) return;
    const interval = setInterval(async () => {
      for (const jobId of pollingIds) {
        try {
          const updated = await jobsApi.get(jobId);
          setItems((prev) =>
            prev.map((j) => (j.id === jobId ? updated : j))
          );
          if (!["pending", "running"].includes(updated.status)) {
            setPollingIds((prev) => {
              const next = new Set(prev);
              next.delete(jobId);
              return next;
            });
          }
        } catch {
          // ignore polling errors
        }
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [pollingIds]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      const job = await jobsApi.create({
        job_type: jobType,
        project_id: projectId || undefined,
        media_id: mediaId || undefined,
      });
      setItems((prev) => [job, ...prev]);
      if (["pending", "running"].includes(job.status)) {
        setPollingIds((prev) => new Set(prev).add(job.id));
      }
      setShowForm(false);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to submit job");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this job?")) return;
    try {
      await jobsApi.delete(id);
      setItems((prev) => prev.filter((j) => j.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete job");
    }
  }

  if (!authenticated) return null;

  return (
    <>
      <NavBar />
      <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">AI Jobs</h1>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            {showForm ? "Cancel" : "+ Submit Job"}
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleSubmit}
            className="bg-white border border-gray-200 rounded-xl p-5 space-y-4"
          >
            <h2 className="font-semibold text-gray-800">New AI Job</h2>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Job type *</label>
              <select
                value={jobType}
                onChange={(e) => setJobType(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {JOB_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Project (optional)</label>
              <select
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">— none —</option>
                {projectsList.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Media ID (optional)</label>
              <input
                value={mediaId}
                onChange={(e) => setMediaId(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="UUID of media file"
              />
            </div>

            {formError && <p className="text-sm text-red-500">{formError}</p>}

            <button
              type="submit"
              disabled={submitting}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
            >
              {submitting ? "Submitting…" : "Submit"}
            </button>
          </form>
        )}

        {loading && <p className="text-gray-500 text-sm">Loading jobs…</p>}
        {error && <p className="text-red-500 text-sm">{error}</p>}
        {!loading && !error && items.length === 0 && (
          <p className="text-gray-500 text-sm">No jobs yet. Submit one above.</p>
        )}

        <ul className="space-y-3">
          {items.map((job) => (
            <li
              key={job.id}
              className="bg-white border border-gray-200 rounded-xl p-5"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-gray-800">{job.job_type}</span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        STATUS_COLORS[job.status] ?? "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {job.status}
                    </span>
                    {pollingIds.has(job.id) && (
                      <span className="text-xs text-gray-400 animate-pulse">polling…</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(job.created_at).toLocaleString()}
                  </p>
                  {job.result && (
                    <details className="mt-2">
                      <summary className="text-xs text-indigo-600 cursor-pointer">View result</summary>
                      <pre className="text-xs bg-gray-50 border border-gray-200 rounded p-2 mt-1 overflow-auto">
                        {JSON.stringify(job.result, null, 2)}
                      </pre>
                    </details>
                  )}
                  {job.error && (
                    <p className="text-xs text-red-500 mt-1">Error: {job.error}</p>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(job.id)}
                  className="text-red-400 hover:text-red-600 text-sm transition-colors shrink-0"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      </main>
    </>
  );
}

export default function JobsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-gray-500">Loading…</div>}>
      <JobsContent />
    </Suspense>
  );
}

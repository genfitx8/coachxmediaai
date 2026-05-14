"use client";

import { useEffect, useState, FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import NavBar from "@/components/NavBar";
import { useRequireAuth } from "@/lib/auth";
import { projects as projectsApi, jobs as jobsApi, ProjectRead } from "@/lib/api";

export default function ProjectDetailPage() {
  const { authenticated } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;

  const [project, setProject] = useState<ProjectRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit form
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Comparison video form
  const [beforeFile, setBeforeFile] = useState<File | null>(null);
  const [afterFile, setAfterFile] = useState<File | null>(null);
  const [rendering, setRendering] = useState(false);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [resultUrl, setResultUrl] = useState<string | null>(null);

  // Slow-motion form
  const [slowFile, setSlowFile] = useState<File | null>(null);
  const [slowSpeed, setSlowSpeed] = useState<number>(0.5);
  const [slowRendering, setSlowRendering] = useState(false);
  const [slowError, setSlowError] = useState<string | null>(null);
  const [slowResultUrl, setSlowResultUrl] = useState<string | null>(null);

  async function handleRenderComparison(e: FormEvent) {
    e.preventDefault();
    if (!beforeFile || !afterFile) {
      setRenderError("Please choose both a 'before' and an 'after' video file.");
      return;
    }
    setRenderError(null);
    setRendering(true);
    if (resultUrl) {
      URL.revokeObjectURL(resultUrl);
      setResultUrl(null);
    }
    try {
      const blob = await jobsApi.comparison(beforeFile, afterFile);
      setResultUrl(URL.createObjectURL(blob));
    } catch (err) {
      setRenderError(err instanceof Error ? err.message : "Render failed");
    } finally {
      setRendering(false);
    }
  }

  async function handleRenderSlowMotion(e: FormEvent) {
    e.preventDefault();
    if (!slowFile) {
      setSlowError("Please choose a video file.");
      return;
    }
    setSlowError(null);
    setSlowRendering(true);
    if (slowResultUrl) {
      URL.revokeObjectURL(slowResultUrl);
      setSlowResultUrl(null);
    }
    try {
      const blob = await jobsApi.slowMotion(slowFile, slowSpeed);
      setSlowResultUrl(URL.createObjectURL(blob));
    } catch (err) {
      setSlowError(err instanceof Error ? err.message : "Render failed");
    } finally {
      setSlowRendering(false);
    }
  }

  useEffect(() => {
    if (!authenticated) return;
    projectsApi.get(id).then((p) => {
      setProject(p);
      setName(p.name);
      setDescription(p.description ?? "");
      setLoading(false);
    }).catch((err) => {
      setError(err instanceof Error ? err.message : "Failed to load project");
      setLoading(false);
    });
  }, [authenticated, id]);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setSaveError(null);
    setSaving(true);
    try {
      const updated = await projectsApi.update(id, {
        name,
        description: description || undefined,
      });
      setProject(updated);
      setEditing(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this project?")) return;
    await projectsApi.delete(id);
    router.replace("/projects");
  }

  if (!authenticated) return null;
  if (loading) return <><NavBar /><main className="max-w-4xl mx-auto px-4 py-8"><p className="text-gray-500">Loading…</p></main></>;
  if (error) return <><NavBar /><main className="max-w-4xl mx-auto px-4 py-8"><p className="text-red-500">{error}</p></main></>;
  if (!project) return null;

  return (
    <>
      <NavBar />
      <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {/* Breadcrumb */}
        <nav className="text-sm text-gray-500">
          <Link href="/projects" className="hover:underline text-indigo-600">Projects</Link>
          {" / "}
          <span className="text-gray-800 font-medium">{project.name}</span>
        </nav>

        {/* Project detail card */}
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          {editing ? (
            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                />
              </div>
              {saveError && <p className="text-sm text-red-500">{saveError}</p>}
              <div className="flex gap-3">
                <button type="submit" disabled={saving} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-60">
                  {saving ? "Saving…" : "Save"}
                </button>
                <button type="button" onClick={() => setEditing(false)} className="text-gray-600 px-4 py-2 rounded-lg text-sm border border-gray-300 hover:bg-gray-50">
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
                {project.description && (
                  <p className="text-gray-600 mt-1">{project.description}</p>
                )}
                <p className="text-xs text-gray-400 mt-2">
                  Created {new Date(project.created_at).toLocaleString()}
                </p>
              </div>
              <div className="flex gap-2 shrink-0 ml-4">
                <button onClick={() => setEditing(true)} className="text-sm border border-gray-300 px-3 py-1.5 rounded-lg hover:bg-gray-50">
                  Edit
                </button>
                <button onClick={handleDelete} className="text-sm border border-red-200 text-red-500 px-3 py-1.5 rounded-lg hover:bg-red-50">
                  Delete
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Quick links */}
        <div className="grid grid-cols-2 gap-4">
          <Link
            href={`/projects/${id}/media`}
            className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-sm transition-shadow"
          >
            <p className="text-lg font-semibold text-gray-800">📁 Media</p>
            <p className="text-sm text-gray-500 mt-1">Upload and manage media files</p>
          </Link>
          <Link
            href={`/jobs?project=${id}`}
            className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-sm transition-shadow"
          >
            <p className="text-lg font-semibold text-gray-800">⚙️ AI Jobs</p>
            <p className="text-sm text-gray-500 mt-1">Submit and track AI processing jobs</p>
          </Link>
        </div>

        {/* Before / After comparison video */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Before / After Comparison</h2>
            <p className="text-sm text-gray-500 mt-1">
              Upload two clips and we&apos;ll render a side-by-side comparison MP4.
              Keep each file under 50&nbsp;MB and roughly 30&nbsp;seconds for best results.
            </p>
          </div>

          <form onSubmit={handleRenderComparison} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Before video
                </label>
                <input
                  type="file"
                  accept="video/*"
                  onChange={(e) => setBeforeFile(e.target.files?.[0] ?? null)}
                  className="w-full text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  After video
                </label>
                <input
                  type="file"
                  accept="video/*"
                  onChange={(e) => setAfterFile(e.target.files?.[0] ?? null)}
                  className="w-full text-sm"
                />
              </div>
            </div>

            {renderError && <p className="text-sm text-red-500">{renderError}</p>}

            <button
              type="submit"
              disabled={rendering || !beforeFile || !afterFile}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
            >
              {rendering ? "Rendering… (can take up to a minute)" : "Render comparison video"}
            </button>
          </form>

          {resultUrl && (
            <div className="pt-4 border-t border-gray-100 space-y-3">
              <video
                src={resultUrl}
                controls
                className="w-full rounded-lg border border-gray-200 bg-black"
              />
              <a
                href={resultUrl}
                download="comparison.mp4"
                className="inline-block text-sm bg-gray-900 text-white px-4 py-2 rounded-lg hover:bg-black"
              >
                Download MP4
              </a>
            </div>
          )}
        </div>

        {/* Slow motion */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Slow Motion</h2>
            <p className="text-sm text-gray-500 mt-1">
              Slow a clip down for swing analysis. Output length =
              input&nbsp;÷&nbsp;speed (½× makes a 5&nbsp;s clip 10&nbsp;s long).
              Keep under 50&nbsp;MB.
            </p>
          </div>

          <form onSubmit={handleRenderSlowMotion} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Video
              </label>
              <input
                type="file"
                accept="video/*"
                onChange={(e) => setSlowFile(e.target.files?.[0] ?? null)}
                className="w-full text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Speed
              </label>
              <select
                value={slowSpeed}
                onChange={(e) => setSlowSpeed(parseFloat(e.target.value))}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value={0.5}>½× (half speed)</option>
                <option value={0.25}>¼× (quarter speed)</option>
                <option value={0.125}>⅛× (eighth speed)</option>
              </select>
            </div>

            {slowError && <p className="text-sm text-red-500">{slowError}</p>}

            <button
              type="submit"
              disabled={slowRendering || !slowFile}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
            >
              {slowRendering ? "Rendering…" : "Render slow-motion video"}
            </button>
          </form>

          {slowResultUrl && (
            <div className="pt-4 border-t border-gray-100 space-y-3">
              <video
                src={slowResultUrl}
                controls
                className="w-full rounded-lg border border-gray-200 bg-black"
              />
              <a
                href={slowResultUrl}
                download={`slow_${slowSpeed}x.mp4`}
                className="inline-block text-sm bg-gray-900 text-white px-4 py-2 rounded-lg hover:bg-black"
              >
                Download MP4
              </a>
            </div>
          )}
        </div>
      </main>
    </>
  );
}

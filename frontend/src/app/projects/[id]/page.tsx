"use client";

import { useEffect, useState, FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import NavBar from "@/components/NavBar";
import { useRequireAuth } from "@/lib/auth";
import { projects as projectsApi, ProjectRead } from "@/lib/api";

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
      </main>
    </>
  );
}

"use client";

import { useEffect, useState, FormEvent } from "react";
import Link from "next/link";
import NavBar from "@/components/NavBar";
import { useRequireAuth } from "@/lib/auth";
import { projects as projectsApi, ProjectRead } from "@/lib/api";

export default function ProjectsPage() {
  const { authenticated } = useRequireAuth();
  const [items, setItems] = useState<ProjectRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New project form
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await projectsApi.list();
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (authenticated) load();
  }, [authenticated]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setCreating(true);
    try {
      await projectsApi.create({ name, description: description || undefined });
      setName("");
      setDescription("");
      setShowForm(false);
      await load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this project?")) return;
    try {
      await projectsApi.delete(id);
      setItems((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete project");
    }
  }

  if (!authenticated) return null;

  return (
    <>
      <NavBar />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            {showForm ? "Cancel" : "+ New Project"}
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleCreate}
            className="bg-white border border-gray-200 rounded-xl p-5 mb-6 space-y-4"
          >
            <h2 className="font-semibold text-gray-800">Create project</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name *
              </label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="My Project"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                placeholder="Optional description"
              />
            </div>
            {formError && (
              <p className="text-sm text-red-500">{formError}</p>
            )}
            <button
              type="submit"
              disabled={creating}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
            >
              {creating ? "Creating…" : "Create"}
            </button>
          </form>
        )}

        {loading && (
          <p className="text-gray-500 text-sm">Loading projects…</p>
        )}
        {error && (
          <p className="text-red-500 text-sm">{error}</p>
        )}
        {!loading && !error && items.length === 0 && (
          <p className="text-gray-500 text-sm">No projects yet. Create one above.</p>
        )}

        <ul className="space-y-3">
          {items.map((project) => (
            <li
              key={project.id}
              className="bg-white border border-gray-200 rounded-xl p-5 flex items-center justify-between"
            >
              <div>
                <Link
                  href={`/projects/${project.id}`}
                  className="text-indigo-600 font-semibold hover:underline"
                >
                  {project.name}
                </Link>
                {project.description && (
                  <p className="text-sm text-gray-500 mt-0.5">
                    {project.description}
                  </p>
                )}
                <p className="text-xs text-gray-400 mt-1">
                  {new Date(project.created_at).toLocaleDateString()}
                </p>
              </div>
              <button
                onClick={() => handleDelete(project.id)}
                className="text-red-400 hover:text-red-600 text-sm transition-colors ml-4"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </main>
    </>
  );
}

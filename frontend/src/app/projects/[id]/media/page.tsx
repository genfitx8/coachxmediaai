"use client";

import { useEffect, useState, ChangeEvent } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import NavBar from "@/components/NavBar";
import { useRequireAuth } from "@/lib/auth";
import { media as mediaApi, MediaRead } from "@/lib/api";

export default function MediaPage() {
  const { authenticated } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const projectId = params.id;

  const [items, setItems] = useState<MediaRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Upload
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await mediaApi.listForProject(projectId);
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load media");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (authenticated) load();
  // load is stable (defined outside effect), projectId comes from params
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authenticated, projectId]);

  async function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError(null);
    setUploading(true);
    try {
      await mediaApi.upload(projectId, file);
      await load();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this media file?")) return;
    try {
      await mediaApi.delete(id);
      setItems((prev) => prev.filter((m) => m.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete");
    }
  }

  function formatBytes(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  if (!authenticated) return null;

  return (
    <>
      <NavBar />
      <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {/* Breadcrumb */}
        <nav className="text-sm text-gray-500">
          <Link href="/projects" className="hover:underline text-indigo-600">Projects</Link>
          {" / "}
          <Link href={`/projects/${projectId}`} className="hover:underline text-indigo-600">Project</Link>
          {" / "}
          <span className="text-gray-800 font-medium">Media</span>
        </nav>

        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Media Files</h1>

          <label className={`cursor-pointer bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors ${uploading ? "opacity-60 pointer-events-none" : ""}`}>
            {uploading ? "Uploading…" : "↑ Upload File"}
            <input
              type="file"
              accept="video/*,audio/*,image/*"
              className="hidden"
              onChange={handleFileChange}
              disabled={uploading}
            />
          </label>
        </div>

        {uploadError && (
          <p className="text-sm text-red-500 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {uploadError}
          </p>
        )}

        {loading && <p className="text-gray-500 text-sm">Loading media…</p>}
        {error && <p className="text-red-500 text-sm">{error}</p>}
        {!loading && !error && items.length === 0 && (
          <p className="text-gray-500 text-sm">No media files yet. Upload one above.</p>
        )}

        <ul className="space-y-3">
          {items.map((item) => (
            <li
              key={item.id}
              className="bg-white border border-gray-200 rounded-xl px-5 py-4 flex items-center justify-between"
            >
              <div>
                <p className="font-medium text-gray-800">{item.filename}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {item.content_type} · {formatBytes(item.size_bytes)} ·{" "}
                  {new Date(item.created_at).toLocaleDateString()}
                </p>
              </div>
              <button
                onClick={() => handleDelete(item.id)}
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

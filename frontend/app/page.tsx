"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { SayCutLogo } from "./components/SayCutLogo";
import { ProjectCard } from "./components/ProjectCard";
import { fetchStorybooks, StorybookSummary } from "./lib/api";

export default function ProjectsPage() {
  const [storybooks, setStorybooks] = useState<readonly StorybookSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStorybooks()
      .then(setStorybooks)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-border-subtle">
        <SayCutLogo size="md" variant="full" />
        <Link href="/project/new">
          <motion.button
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
            className="px-4 py-2 rounded-lg bg-accent-cyan text-bg-primary font-display text-sm font-semibold transition-colors hover:brightness-110"
          >
            + New Project
          </motion.button>
        </Link>
      </header>

      {/* Content */}
      <main className="flex-1 px-6 py-8 max-w-6xl mx-auto w-full">
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="h-6 w-6 rounded-full border-2 border-accent-cyan border-t-transparent animate-spin" />
          </div>
        )}

        {error && (
          <div className="text-center py-20">
            <p className="text-accent-red text-sm">{error}</p>
            <p className="text-text-muted text-xs mt-2">
              Make sure the backend is running on port 3001
            </p>
          </div>
        )}

        {!loading && !error && storybooks.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 gap-6">
            <SayCutLogo size="xl" variant="mark" />
            <div className="text-center">
              <h2 className="font-display text-lg text-text-primary">
                Create your first storybook
              </h2>
              <p className="text-text-muted text-sm mt-1">
                Describe a story with your voice and watch it come to life
              </p>
            </div>
            <Link href="/project/new">
              <motion.button
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.97 }}
                className="px-6 py-3 rounded-lg bg-accent-cyan text-bg-primary font-display text-sm font-semibold transition-colors hover:brightness-110"
              >
                + New Project
              </motion.button>
            </Link>
          </div>
        )}

        {!loading && !error && storybooks.length > 0 && (
          <>
            <h2 className="font-display text-sm text-text-muted mb-4">
              Your Projects
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {storybooks.map((sb) => (
                <ProjectCard
                  key={sb.id}
                  id={sb.id}
                  title={sb.title}
                  thumbnailUrl={sb.thumbnailUrl}
                  sceneCount={sb.sceneCount}
                  createdAt={sb.createdAt}
                />
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}

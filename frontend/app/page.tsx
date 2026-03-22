"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { SayCutLogo } from "./components/SayCutLogo";
import { ProjectCard } from "./components/ProjectCard";
import { fetchStorybooks, StorybookSummary } from "./lib/api";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.15 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: "easeOut" as const },
  },
};

const fadeUpVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: "easeOut" as const },
  },
};

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

  const featured = storybooks.length > 0 ? storybooks[0] : null;
  const rest = storybooks.length > 1 ? storybooks.slice(1) : [];

  return (
    <div className="min-h-screen flex flex-col relative lobby-bg vignette lobby-grain">
      {/* Header */}
      <header className="flex items-center justify-between px-6 md:px-10 py-5 header-glow relative z-10">
        <div>
          <SayCutLogo size="md" variant="full" />
          <p className="text-text-muted/50 text-[10px] font-body italic mt-0.5 ml-0.5">
            Stories told by voice, brought to life by AI
          </p>
        </div>
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
      <main className="flex-1 px-6 md:px-10 py-8 max-w-6xl mx-auto w-full relative z-10">
        {/* Loading */}
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center justify-center py-20"
          >
            <div className="h-6 w-6 rounded-full border-2 border-accent-cyan border-t-transparent animate-spin" />
          </motion.div>
        )}

        {/* Error */}
        {error && (
          <div className="text-center py-20">
            <p className="text-accent-red text-sm">{error}</p>
            <p className="text-text-muted text-xs mt-2">
              Make sure the backend is running on port 3001
            </p>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && storybooks.length === 0 && (
          <div className="relative flex flex-col items-center justify-center py-24 gap-6 overflow-hidden">
            {/* Bokeh circles */}
            <div
              className="bokeh-circle bokeh-1"
              style={{
                width: 120,
                height: 120,
                background: "rgba(217,119,87,0.25)",
                top: "10%",
                left: "20%",
              }}
            />
            <div
              className="bokeh-circle bokeh-2"
              style={{
                width: 80,
                height: 80,
                background: "rgba(212,165,116,0.2)",
                top: "60%",
                right: "15%",
              }}
            />
            <div
              className="bokeh-circle bokeh-3"
              style={{
                width: 60,
                height: 60,
                background: "rgba(120,140,93,0.2)",
                bottom: "15%",
                left: "35%",
              }}
            />

            <motion.div
              variants={fadeUpVariants}
              initial="hidden"
              animate="visible"
              className="flex flex-col items-center gap-6 relative z-10"
            >
              <SayCutLogo size="xl" variant="mark" />
              <div className="text-center">
                <h2 className="font-display text-2xl text-text-primary">
                  Create your first storybook
                </h2>
                <p className="font-body text-text-muted/70 text-sm mt-2 max-w-sm">
                  Describe a story with your voice and watch it come to life as
                  scenes, images, and video
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
            </motion.div>
          </div>
        )}

        {/* Projects listing */}
        {!loading && !error && storybooks.length > 0 && (
          <>
            {/* Section header */}
            <motion.div
              variants={fadeUpVariants}
              initial="hidden"
              animate="visible"
              className="mb-6"
            >
              <h2 className="font-display text-xl text-text-primary tracking-tight section-accent">
                Your Projects
              </h2>
              <p className="font-body italic text-text-muted/60 text-xs mt-3">
                {storybooks.length}{" "}
                {storybooks.length === 1
                  ? "story waiting to be told"
                  : "stories waiting to be told"}
              </p>
            </motion.div>

            {/* Featured (latest) project */}
            {featured && (
              <motion.div
                variants={cardVariants}
                initial="hidden"
                animate="visible"
                className="mb-5"
              >
                <ProjectCard
                  id={featured.id}
                  title={featured.title}
                  thumbnailUrl={featured.thumbnailUrl}
                  sceneCount={featured.sceneCount}
                  createdAt={featured.createdAt}
                  featured
                />
              </motion.div>
            )}

            {/* Film-strip divider */}
            {rest.length > 0 && <div className="film-divider my-6" />}

            {/* Rest of projects in staggered grid */}
            {rest.length > 0 && (
              <motion.div
                variants={containerVariants}
                initial="hidden"
                animate="visible"
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
              >
                {rest.map((sb) => (
                  <motion.div key={sb.id} variants={cardVariants}>
                    <ProjectCard
                      id={sb.id}
                      title={sb.title}
                      thumbnailUrl={sb.thumbnailUrl}
                      sceneCount={sb.sceneCount}
                      createdAt={sb.createdAt}
                      mode={sb.mode}
                    />
                  </motion.div>
                ))}
              </motion.div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

"use client";

import Link from "next/link";
import { motion } from "framer-motion";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:3001";

function prefixUrl(url: string | null): string | null {
  if (!url) return null;
  if (url.startsWith("http")) return url;
  return `${BACKEND_URL}${url}`;
}

function relativeDate(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

interface ProjectCardProps {
  readonly id: string;
  readonly title: string;
  readonly thumbnailUrl: string | null;
  readonly sceneCount: number;
  readonly createdAt: string;
}

export function ProjectCard({
  id,
  title,
  thumbnailUrl,
  sceneCount,
  createdAt,
}: ProjectCardProps) {
  const thumb = prefixUrl(thumbnailUrl);

  return (
    <Link href={`/project/${id}`}>
      <motion.div
        whileHover={{ scale: 1.03, y: -2 }}
        transition={{ duration: 0.2 }}
        className="group cursor-pointer rounded-xl overflow-hidden border border-border-subtle bg-bg-surface/60 hover:border-accent-cyan/40 transition-colors"
      >
        {/* Thumbnail */}
        <div className="aspect-video bg-bg-elevated relative overflow-hidden">
          {thumb ? (
            <img
              src={thumb}
              alt={title}
              className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-bg-elevated to-bg-primary">
              <span className="text-3xl text-text-muted/30 font-display">
                SC
              </span>
            </div>
          )}
          {/* Scene count badge */}
          <span className="absolute bottom-2 right-2 px-2 py-0.5 rounded-full bg-black/60 text-[11px] font-display text-text-muted backdrop-blur-sm">
            {sceneCount} {sceneCount === 1 ? "scene" : "scenes"}
          </span>
        </div>

        {/* Info */}
        <div className="px-3 py-2.5">
          <h3 className="font-display text-sm text-text-primary truncate">
            {title}
          </h3>
          <p className="text-[11px] text-text-muted mt-0.5">
            {relativeDate(createdAt)}
          </p>
        </div>
      </motion.div>
    </Link>
  );
}

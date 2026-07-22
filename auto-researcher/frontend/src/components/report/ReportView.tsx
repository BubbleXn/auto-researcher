"use client";

import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { ReportActions } from "./ReportActions";
import { ExternalLink } from "lucide-react";
import { cn } from "@/lib/cn";

interface ReportViewProps {
  markdown: string;
}

function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return url;
  }
}

export function ReportView({ markdown }: ReportViewProps) {
  return (
    <div className="py-6">
      <ReportActions markdown={markdown} />
      <article className="prose max-w-none [&_h1]:text-text-primary [&_h1]:text-xl [&_h1]:font-semibold [&_h2]:text-text-primary [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:border-b [&_h2]:border-surface-500/20 [&_h2]:pb-2 [&_p]:text-text-secondary [&_p]:leading-relaxed [&_blockquote]:border-l-surface-500 [&_blockquote]:text-text-tertiary [&_code]:text-link [&_code]:bg-surface-700 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded-md [&_code]:text-sm [&_pre]:bg-surface-900 [&_pre]:border [&_pre]:border-surface-500/20 [&_pre]:rounded-xl [&_table]:text-sm [&_th]:text-text-primary [&_th]:bg-surface-700 [&_td]:border-surface-500/20 [&_th]:border-surface-500/20 [&_li]:text-text-secondary [&_hr]:border-surface-500/20">
        <Markdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeHighlight]}
          components={{
            a: ({ href, children, ...props }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(
                  "inline-flex items-center gap-0.5 text-link no-underline hover:underline",
                  "bg-phase-searching/8 px-0.5 rounded citation-link"
                )}
                title={href ? `来源: ${getDomain(href)}` : undefined}
                {...props}
              >
                {children}
                <ExternalLink className="inline w-3 h-3 opacity-40" />
              </a>
            ),
          }}
        >
          {markdown}
        </Markdown>
      </article>
    </div>
  );
}

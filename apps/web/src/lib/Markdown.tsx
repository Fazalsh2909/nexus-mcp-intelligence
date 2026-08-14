import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown-body text-[13px] leading-relaxed text-foreground/95">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ ...props }) => (
            <a {...props} target="_blank" rel="noopener noreferrer" className="text-foreground underline underline-offset-2 hover:text-muted" />
          ),
          code: ({ className, children, ...props }) => {
            const inline = !className
            return inline ? (
              <code
                className="mono rounded-[3px] border border-border bg-surface-2 px-1 py-px text-[12px] text-foreground"
                {...props}
              >
                {children}
              </code>
            ) : (
              <code
                className={`mono block overflow-x-auto rounded-md border border-border bg-background px-3 py-2.5 text-[12px] text-foreground ${className ?? ''}`}
                {...props}
              >
                {children}
              </code>
            )
          },
          pre: ({ children }) => <pre className="my-2">{children}</pre>,
          h1: ({ children }) => <h1 className="mb-1.5 mt-3 text-[15px] font-semibold text-foreground">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-1.5 mt-3 text-[14px] font-semibold text-foreground">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-1 mt-2.5 text-[13px] font-semibold text-foreground">{children}</h3>,
          ul: ({ children }) => <ul className="my-1.5 list-disc space-y-1 pl-5 marker:text-faint">{children}</ul>,
          ol: ({ children }) => <ol className="my-1.5 list-decimal space-y-1 pl-5 marker:text-faint">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="my-2 border-l-2 border-border-strong pl-3 text-muted">{children}</blockquote>
          ),
          hr: () => <hr className="my-3 border-border" />,
          table: ({ children }) => (
            <div className="my-2.5 overflow-x-auto rounded-md border border-border">
              <table className="w-full border-collapse text-[12.5px]">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-surface-2/70 text-left">{children}</thead>,
          th: ({ children }) => <th className="border-b border-border px-3 py-1.5 font-medium text-muted">{children}</th>,
          td: ({ children }) => <td className="border-b border-border/60 px-3 py-1.5 align-top text-foreground/90">{children}</td>,
          tr: ({ children }) => <tr>{children}</tr>,
          p: ({ children }) => <p className="my-1.5">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}

// Safety note: dangerouslySetInnerHTML is used intentionally here for JSON-LD
// structured data. The `data` prop is always sourced from our own database (never
// user-supplied raw HTML), so XSS is not a risk. JSON.stringify produces valid JSON,
// which browsers parse as data — not executable HTML.

interface JsonLdProps {
  data: Record<string, unknown>;
}

export function JsonLd({ data }: JsonLdProps) {
  console.assert(typeof data === "object" && data !== null, "JsonLd: data must be a non-null object");
  console.assert("@context" in data, "JsonLd: data must include @context");

  const json = JSON.stringify(data);

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: json }}
    />
  );
}

type JsonPreviewProps = {
  value: unknown;
};

export function JsonPreview({ value }: JsonPreviewProps) {
  return <pre className="json-preview">{JSON.stringify(value, null, 2)}</pre>;
}

export function formatNumber(
  value: number | null | undefined,
  digits = 1,
): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  return value.toFixed(digits);
}

export function formatInteger(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  return String(Math.round(value));
}

export function formatBoolean(
  value: boolean | null | undefined,
  trueLabel = "yes",
  falseLabel = "no",
): string {
  if (value === undefined || value === null) {
    return "-";
  }
  return value ? trueLabel : falseLabel;
}

export function formatText(value: string | number | null | undefined): string {
  if (value === undefined || value === null || value === "") {
    return "-";
  }
  return String(value);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

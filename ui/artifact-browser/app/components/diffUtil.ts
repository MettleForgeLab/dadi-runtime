export type DiffItem =
  | { kind: "added"; path: string; b: any }
  | { kind: "removed"; path: string; a: any }
  | { kind: "changed"; path: string; a: any; b: any };

function isObject(v: any): v is Record<string, any> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

export function diffJson(a: any, b: any, basePath = ""): DiffItem[] {
  if (a === b) return [];
  const path = basePath || "$";

  // Array: compare by index
  if (Array.isArray(a) && Array.isArray(b)) {
    const out: DiffItem[] = [];
    const n = Math.max(a.length, b.length);
    for (let i = 0; i < n; i++) {
      const p = `${path}[${i}]`;
      if (i >= a.length) out.push({ kind: "added", path: p, b: b[i] });
      else if (i >= b.length) out.push({ kind: "removed", path: p, a: a[i] });
      else out.push(...diffJson(a[i], b[i], p));
    }
    return out;
  }

  // Objects: compare keys
  if (isObject(a) && isObject(b)) {
    const out: DiffItem[] = [];
    const aKeys = Object.keys(a);
    const bKeys = Object.keys(b);
    const keys = Array.from(new Set([...aKeys, ...bKeys])).sort();
    for (const k of keys) {
      const p = path === "$" ? `$.${k}` : `${path}.${k}`;
      if (!(k in a)) out.push({ kind: "added", path: p, b: b[k] });
      else if (!(k in b)) out.push({ kind: "removed", path: p, a: a[k] });
      else out.push(...diffJson(a[k], b[k], p));
    }
    return out;
  }

  return [{ kind: "changed", path, a, b }];
}

export interface CompletedLabRecord {
  completedAt: string;
  xp: number;
}

const STORAGE_KEY = "utss_lab_progress";

export function getCompletedLabs(): Record<string, CompletedLabRecord> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function isLabCompleted(queryId: string): boolean {
  const completed = getCompletedLabs();
  return Boolean(completed[queryId]);
}

export function markLabCompleted(queryId: string, xp: number): void {
  try {
    const completed = getCompletedLabs();
    if (!completed[queryId]) {
      completed[queryId] = {
        completedAt: new Date().toISOString(),
        xp
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(completed));
      window.dispatchEvent(new CustomEvent("utss-lab-updated", { detail: { queryId, xp } }));
    }
  } catch (err) {
    console.error("Failed to save lab progress to localStorage", err);
  }
}

export function getTotalLabXp(): number {
  const completed = getCompletedLabs();
  return Object.values(completed).reduce((sum, item) => sum + (item.xp || 0), 0);
}

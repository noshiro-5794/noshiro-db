export function buildYearDays(year: number) {
  const days: string[] = [];
  const cursor = new Date(Date.UTC(year, 0, 1));
  const end = new Date(Date.UTC(year + 1, 0, 1));
  while (cursor < end) {
    days.push(cursor.toISOString().slice(0, 10));
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return days;
}

export function getWeekIndex(date: string) {
  const day = new Date(`${date}T00:00:00Z`);
  const start = new Date(Date.UTC(day.getUTCFullYear(), 0, 1));
  const offset = start.getUTCDay();
  return Math.floor((offset + Math.floor((day.getTime() - start.getTime()) / 86_400_000)) / 7);
}

export function contributionLevel(count: number) {
  if (count <= 0) return 0;
  if (count === 1) return 1;
  if (count <= 3) return 2;
  if (count <= 6) return 3;
  return 4;
}

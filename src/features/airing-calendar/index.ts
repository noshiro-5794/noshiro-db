/**
 * Airing calendar slice.
 *
 * Presentation for the broadcast schedule: the month grid, the shared time
 * surface for week and day, the per-weekday broadcast board and the detail
 * card, plus the date model they are built on. Import everything from here so
 * the slice keeps a single public surface.
 */

import './ui/calendar.css';

export {
  AIRING_TIME_ZONE,
  AIRING_TIME_ZONE_LABEL,
  addDays,
  boardWindow,
  buildOccurrences,
  groupOccurrences,
  isWithin,
  monthGridRange,
  occurrenceFor,
  rangeDays,
  shiftMonth,
  startOfWeek,
  weekRange,
  type CalendarOccurrence,
} from './model/calendar-model';
export { BroadcastBoard } from './ui/BroadcastBoard';
export { EventDetails } from './ui/EventDetails';
export { MonthGrid } from './ui/MonthGrid';
export { IconButton, SegmentedControl } from './ui/primitives';
export { TimeGrid } from './ui/TimeGrid';

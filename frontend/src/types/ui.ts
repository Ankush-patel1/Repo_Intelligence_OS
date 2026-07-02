export type SortDirection = "asc" | "desc";

export interface SortOption {
  field: string;
  direction: SortDirection;
}

export interface FilterOption {
  field: string;
  value: string | number | boolean;
}
